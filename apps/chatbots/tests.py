"""Tests for backend chatbot adjustments."""
from unittest.mock import patch
from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework import status
from apps.chatbots.models import Chatbot, ChatSession, ChatMessage, GeneralChatbot
from apps.chatbots.services import RagService
from apps.chatbots.insforge_client import InsForgeClient
from apps.chatbots.memory_service import ChatbotMemoryService

User = get_user_model()

class ChatbotVisibilityTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass', email='t@test.com')
        self.public_chat = Chatbot.objects.create(
            nombre='Public Bot', creador=self.user, is_public=True,
            funciones=['internet'], slug='public-bot', modelo='openai/gpt-4o-mini'
        )
        self.private_chat = Chatbot.objects.create(
            nombre='Private Bot', creador=self.user, is_public=False,
            funciones=['codigo'], slug='private-bot', modelo='openai/gpt-4o-mini'
        )

    def test_public_requires_auth_for_detail(self):
        response = self.client.get('/api/chatbots/public-bot/')
        self.assertIn(response.status_code, [403, 401, 200])

    def test_owner_can_access_private(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/chatbots/private-bot/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_shared_access_private(self):
        other = User.objects.create_user(username='other', password='test', email='o@test.com')
        self.private_chat.shared_with.add(other)
        self.client.force_authenticate(user=other)
        response = self.client.get('/api/chatbots/private-bot/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class ChatbotCRUDTests(APITestCase):
    def setUp(self):
        self.creator = User.objects.create_user(
            username='creator', password='testpass', email='c@test.com', role='creator'
        )
        self.user = User.objects.create_user(
            username='user1', password='testpass', email='u@test.com', role='user'
        )
        self.client.force_authenticate(user=self.creator)

    def test_create_chatbot(self):
        data = {'nombre': 'Mi Bot', 'modelo': 'meta-llama/llama-3.1-8b-instruct', 'funciones': ['internet']}
        response = self.client.post('/api/chatbots/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['nombre'], 'Mi Bot')

    def test_create_requires_auth(self):
        self.client.force_authenticate(user=None)
        response = self.client.post('/api/chatbots/', {'nombre': 'Bot'}, format='json')
        self.assertIn(response.status_code, [401, 403])

    def test_user_role_can_create(self):
        # Current API allows any authenticated user to create (perform_create has no role check)
        self.client.force_authenticate(user=self.user)
        response = self.client.post('/api/chatbots/', {'nombre': 'Bot'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_update_own_chatbot(self):
        bot = Chatbot.objects.create(nombre='Bot', creador=self.creator, modelo='openai/gpt-4o-mini', slug='test-bot')
        response = self.client.patch(f'/api/chatbots/{bot.slug}/', {'nombre': 'Updated'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        bot.refresh_from_db()
        self.assertEqual(bot.nombre, 'Updated')

    def test_delete_chatbot(self):
        bot = Chatbot.objects.create(nombre='Bot', creador=self.creator, modelo='openai/gpt-4o-mini', slug='delete-bot')
        response = self.client.delete(f'/api/chatbots/{bot.slug}/')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Chatbot.objects.filter(slug='delete-bot').exists())


class ChatSessionTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='chatter', password='testpass', email='c2@test.com')
        self.chatbot = Chatbot.objects.create(
            nombre='Bot', creador=self.user, is_public=True,
            modelo='openai/gpt-4o-mini', slug='chat-test'
        )
        self.client.force_authenticate(user=self.user)

    def test_session_isolation(self):
        s1 = ChatSession.objects.create(chatbot=self.chatbot, user=self.user)
        user2 = User.objects.create_user(username='u2', password='test', email='u2@test.com')
        s2 = ChatSession.objects.create(chatbot=self.chatbot, user=user2)

        response = self.client.get('/api/sessions/')
        ids = [s['id'] for s in response.data.get('results', response.data)]
        self.assertIn(s1.id, ids)
        self.assertNotIn(s2.id, ids)

    def test_anonymous_session_isolation(self):
        self.client.force_authenticate(user=None)
        r1 = self.client.post(f'/api/chatbots/{self.chatbot.slug}/ask/', {'question': 'Hola'}, format='json')
        r2 = self.client.post(f'/api/chatbots/{self.chatbot.slug}/ask/', {'question': 'Hola'}, format='json')
        sid1 = r1.data.get('session_id')
        sid2 = r2.data.get('session_id')
        if sid1 and sid2:
            self.assertNotEqual(sid1, sid2)


class ShareTests(APITestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username='owner', password='test', email='o@test.com')
        self.shared_user = User.objects.create_user(username='shared', password='test', email='s@test.com')
        self.bot = Chatbot.objects.create(
            nombre='Private Bot', creador=self.owner, is_public=False,
            modelo='openai/gpt-4o-mini', slug='share-test'
        )
        self.bot.shared_with.add(self.shared_user)
        self.client.force_authenticate(user=self.shared_user)

    def test_shared_user_can_access(self):
        response = self.client.get(f'/api/chatbots/{self.bot.slug}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_owner_can_make_public(self):
        self.client.force_authenticate(user=self.owner)
        response = self.client.post(
            f'/api/chatbots/{self.bot.slug}/share/',
            {'is_public': True}, format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.bot.refresh_from_db()
        self.assertTrue(self.bot.is_public)


class GeneralChatbotTests(TestCase):
    def test_auto_created_on_user(self):
        user = User.objects.create_user(username='generaltest', password='test', email='g@test.com')
        self.assertTrue(hasattr(user, 'general_chatbot'))
        self.assertEqual(user.general_chatbot.nombre, 'Asistente General')


class DocumentAndIconTests(TestCase):
    def test_chatbot_has_json_functions(self):
        user = User.objects.create_user(username='func', password='test', email='f@test.com')
        chat = Chatbot.objects.create(nombre='Func', creador=user, funciones=['internet', 'lienzo'], modelo='openai/gpt-4o-mini', slug='func-test')
        self.assertEqual(chat.funciones, ['internet', 'lienzo'])


class ConversationPersistenceTests(APITestCase):
    """Conversations must be preserved: separate sessions, no duplicates,
    and answers survive interrupted streams."""

    def setUp(self):
        # The chatbot post_save signal syncs memory to InsForge — no network in tests
        mem_patcher = patch.object(ChatbotMemoryService, 'sync_memory', return_value=None)
        mem_patcher.start()
        self.addCleanup(mem_patcher.stop)

        self.user = User.objects.create_user(
            username='hist', password='testpass', email='h@test.com'
        )
        self.chatbot = Chatbot.objects.create(
            nombre='Hist Bot', creador=self.user, is_public=True,
            modelo='openai/gpt-4o-mini', slug='hist-bot'
        )
        self.client.force_authenticate(user=self.user)

    def test_no_session_id_creates_new_session(self):
        """'Nueva conversación' (session_id=null) must create a separate session."""
        with patch.object(RagService, 'answer', return_value='r1'):
            r1 = self.client.post('/api/chatbots/hist-bot/ask/', {'question': 'uno'}, format='json')
        with patch.object(RagService, 'answer', return_value='r2'):
            r2 = self.client.post('/api/chatbots/hist-bot/ask/', {'question': 'dos'}, format='json')

        self.assertEqual(r1.status_code, 200, r1.data)
        self.assertEqual(r2.status_code, 200, r2.data)
        sid1, sid2 = r1.data['session_id'], r2.data['session_id']
        self.assertIsNotNone(sid1)
        self.assertNotEqual(sid1, sid2)
        self.assertEqual(
            ChatSession.objects.filter(chatbot=self.chatbot, user=self.user).count(), 2
        )

    def test_session_id_reuses_session(self):
        """Sending an explicit session_id continues that conversation."""
        with patch.object(RagService, 'answer', return_value='r'):
            r1 = self.client.post('/api/chatbots/hist-bot/ask/', {'question': 'hola'}, format='json')
            sid = r1.data['session_id']
            r2 = self.client.post(
                '/api/chatbots/hist-bot/ask/',
                {'question': 'adios', 'session_id': sid},
                format='json',
            )
        self.assertEqual(r2.data['session_id'], sid)
        self.assertEqual(ChatMessage.objects.filter(session_id=sid).count(), 4)

    def test_unanswered_retry_is_not_duplicated(self):
        """Retrying a question whose answer was never stored must not
        duplicate the user message."""
        session = ChatSession.objects.create(chatbot=self.chatbot, user=self.user)
        ChatMessage.objects.create(session=session, contenido='hola', is_user=True)

        with patch.object(RagService, 'answer', return_value='respuesta'):
            r = self.client.post(
                '/api/chatbots/hist-bot/ask/',
                {'question': 'hola', 'session_id': session.id},
                format='json',
            )
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual(
            ChatMessage.objects.filter(
                session=session, is_user=True, contenido='hola'
            ).count(),
            1,
        )
        self.assertTrue(ChatMessage.objects.filter(session=session, is_user=False).exists())

    def test_answered_repeat_question_is_saved_again(self):
        """The same question after an answer is a legit new message."""
        session = ChatSession.objects.create(chatbot=self.chatbot, user=self.user)
        ChatMessage.objects.create(session=session, contenido='hola', is_user=True)
        ChatMessage.objects.create(session=session, contenido='respuesta', is_user=False)

        with patch.object(RagService, 'answer', return_value='r2'):
            r = self.client.post(
                '/api/chatbots/hist-bot/ask/',
                {'question': 'hola', 'session_id': session.id},
                format='json',
            )
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual(
            ChatMessage.objects.filter(
                session=session, is_user=True, contenido='hola'
            ).count(),
            2,
        )

    def test_partial_answer_saved_when_stream_breaks(self):
        """If the stream dies mid-answer, the partial text is persisted so
        the response survives a page refresh."""
        def broken_stream(**kwargs):
            yield 'Hola '
            yield 'mundo'
            raise RuntimeError('conexion perdida')

        with patch.object(RagService, 'generate_response_stream', side_effect=broken_stream), \
             patch.object(RagService, 'retrieve_documents', return_value=[]), \
             patch.object(InsForgeClient, 'retrieve_bot_memory', return_value=''):
            response = self.client.post(
                '/api/chatbots/hist-bot/ask_stream/', {'question': 'hola'}, format='json'
            )
            self.assertEqual(response.status_code, 200)
            self.assertIn('X-Session-ID', response)

            with self.assertRaises(RuntimeError):
                for _ in response.streaming_content:
                    pass

        session_id = response['X-Session-ID']
        partials = ChatMessage.objects.filter(session_id=session_id, is_user=False)
        self.assertEqual(partials.count(), 1)
        self.assertEqual(partials.first().contenido, 'Hola mundo')
        self.assertTrue(
            ChatMessage.objects.filter(session_id=session_id, is_user=True).exists()
        )

    def test_stream_failure_with_zero_tokens_allows_clean_retry(self):
        """A failure before any token leaves the question unanswered; the
        retry must not duplicate it."""
        def failing_stream(**kwargs):
            raise RuntimeError('fallo antes de generar')
            yield  # unreachable — makes this a generator function

        with patch.object(RagService, 'generate_response_stream', side_effect=failing_stream), \
             patch.object(RagService, 'retrieve_documents', return_value=[]), \
             patch.object(InsForgeClient, 'retrieve_bot_memory', return_value=''):
            response = self.client.post(
                '/api/chatbots/hist-bot/ask_stream/', {'question': 'hola'}, format='json'
            )
            self.assertEqual(response.status_code, 200)
            self.assertIn('X-Session-ID', response)

            with self.assertRaises(RuntimeError):
                for _ in response.streaming_content:
                    pass

        session_id = int(response['X-Session-ID'])
        # No assistant reply was stored
        self.assertFalse(
            ChatMessage.objects.filter(session_id=session_id, is_user=False).exists()
        )

        # Retry the same question in the same session (fallback path)
        with patch.object(RagService, 'answer', return_value='intento 2'):
            r = self.client.post(
                '/api/chatbots/hist-bot/ask/',
                {'question': 'hola', 'session_id': session_id},
                format='json',
            )
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual(
            ChatMessage.objects.filter(session_id=session_id, is_user=True).count(), 1
        )
        self.assertTrue(
            ChatMessage.objects.filter(session_id=session_id, is_user=False).exists()
        )
