import secrets
import psycopg2
from psycopg2 import pool
from datetime import datetime
import os
import nltk
from nltk.tokenize import sent_tokenize, word_tokenize
from nltk.corpus import stopwords
from nltk.probability import FreqDist
import torch
from transformers import pipeline, AutoModelForSeq2SeqLM, AutoTokenizer
import asyncio
nltk.data.path.append("/app-data/.cache")
nltk.download('punkt')
nltk.download('punkt_tab')

class ChatContext:
    def __init__(self, prompt_file='/app/lib/chat_history/system_prompt.txt'):
        self.db_url = os.getenv('DATABASE_URL')
        if not self.db_url:
            raise ValueError("DATABASE_URL environment variable not set")
        self.system_prompt = None  # Initialize as None
        self.session_id = None
        self.chat_history = {"messages": [], "commands": []}
        self.trim_count = 0
        self.conn_pool = None  # Initialize as None
        self.summarizer = None  # Initialize as None

        # If no running loop, create a new one
        loop = asyncio.get_running_loop() 

        # Schedule the async operations to run on the loop
        loop.create_task(self._async_init(prompt_file))

        # No need to close the loop if it was retrieved with get_running_loop()

    async def _async_init(self, prompt_file):
        """Asynchronous initialization tasks."""
        self.system_prompt = await self._load_system_prompt(prompt_file)
        self.conn_pool = await self._initialize_connection_pool()
        await self._initialize_db()
        await self._initialize_summarization_model()
    async def _initialize_connection_pool(self):
        try:
            pool = psycopg2.pool.SimpleConnectionPool(1, 10, self.db_url)
            if pool:
                print("Connection pool created successfully")
            return pool
        except Exception as e:
            print(f"Error creating connection pool: {e}")
            raise

    async def _check_connection(self):
        try:
            conn = await self._get_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT 1')
            await self._release_connection(conn)
        except (Exception, psycopg2.DatabaseError) as error:
            print(f"Database connection lost: {error}")
            self.conn_pool = await self._initialize_connection_pool()

    async def _get_connection(self):
        try:
            conn = self.conn_pool.getconn()
            if conn:
                return conn
        except Exception as e:
            print(f"Error getting connection from pool: {e}")
            raise

    async def _release_connection(self, conn):
        try:
            self.conn_pool.putconn(conn)
        except Exception as e:
            print(f"Error releasing connection back to pool: {e}")

    async def _load_system_prompt(self, prompt_file):
        """
        Load the system prompt from a file. If the file is not found,
        fall back to a basic system prompt.
        """
        if os.path.exists(prompt_file):
            try:
                with open(prompt_file, 'r', encoding='utf-8') as f:
                    print(f"Loaded system prompt from {prompt_file}")
                    return f.read()
            except Exception as e:
                print(f"Error reading {prompt_file}: {e}")
        
        print(f"Using default basic system prompt as {prompt_file} was not found.")
        # Basic system prompt as fallback
        return """
You are a helpful AI assistant. Use [EXECUTE] for system commands and [PYTHON] for Python code.
Example:
[EXECUTE]ls -l[/EXECUTE]
[PYTHON]
print("Hello, world!")
[/PYTHON]
"""
    async def _initialize_summarization_model(self):
        """Initializes the summarization model and tokenizer."""
        try:
            # Set custom cache directory
            os.environ['TRANSFORMERS_CACHE'] = '/app-data/.cache'
            os.environ['HF_HOME'] = '/app-data/.cache'

            # Ensure cache directory exists
            os.makedirs('/app-data/.cache', exist_ok=True)

            # Use t5-small for lower memory usage (around 250MB)
            model_name = "t5-small"

            try:
                self.tokenizer = AutoTokenizer.from_pretrained(
                    model_name,
                    cache_dir='/app-data/.cache',
                    local_files_only=True
                )
                self.model = AutoModelForSeq2SeqLM.from_pretrained(
                    model_name,
                    cache_dir='/app-data/.cache',
                    local_files_only=True
                )
            except Exception as e:
                print(f"Local model not found, downloading: {e}")
                self.tokenizer = AutoTokenizer.from_pretrained(
                    model_name,
                    cache_dir='/app-data/.cache'
                )
                self.model = AutoModelForSeq2SeqLM.from_pretrained(
                    model_name,
                    cache_dir='/app-data/.cache'
                )

            # Move to CPU to save memory
            self.model = self.model.to('cpu')

            # Create summarization pipeline
            self.summarizer = pipeline(
                'summarization',
                model=self.model,
                tokenizer=self.tokenizer,
                device=-1  # Use CPU
            )

        except Exception as e:
            print(f"AI summarization model initialization failed: {e}")

    async def _initialize_db(self):
        conn = await self._get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS sessions (
                        id SERIAL PRIMARY KEY,
                        session_id TEXT UNIQUE,
                        timestamp TIMESTAMP,
                        summary TEXT,
                        trim_count INTEGER DEFAULT 0
                    )
                ''')
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS messages (
                        id SERIAL PRIMARY KEY,
                        role TEXT,
                        session_id TEXT,
                        content TEXT,
                        timestamp TIMESTAMP,
                        FOREIGN KEY(session_id) REFERENCES sessions(session_id)
                    )
                ''')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_session_id ON messages (session_id)')
                conn.commit()
        except Exception as e:
            print(f"Error initializing database: {e}")
            conn.rollback()
        finally:
            await self._release_connection(conn)

    async def new_conversation(self):
        await self._check_connection()
        timestamp = datetime.now().isoformat()
        summary = "New conversation"
        self.session_id = secrets.token_hex(32)  # Generate a 64-bit random hex string
        self.chat_history = {"messages": [], "commands": []}
        self.trim_count = 0
        conn = await self._get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute('INSERT INTO sessions (session_id, timestamp, summary, trim_count) VALUES (%s, %s, %s, %s)', (self.session_id, timestamp, summary, self.trim_count))
                conn.commit()
            await self.save_chat_message("system", f"New conversation started. Trim count: {self.trim_count}")
        except Exception as e:
            print(f"Error starting new conversation: {e}")
            conn.rollback()
        finally:
            await self._release_connection(conn)

    async def list_sessions(self):
        await self._check_connection()
        summaries = []
        conn = await self._get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute('SELECT session_id, timestamp, summary, trim_count FROM sessions ORDER BY timestamp DESC')
                sessions = cursor.fetchall()
                for session in sessions:
                    summaries.append({
                        "session_id": session[0],
                        "timestamp": session[1],
                        "summary": session[2],
                        "trim_count": session[3]
                    })
        except Exception as e:
            print(f"Error listing sessions: {e}")
        finally:
            await self._release_connection(conn)
        return summaries

    async def _load_chat_history(self):
        await self._check_connection()
        if self.session_id is None:
            return {"messages": [], "commands": []}
        conn = await self._get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute('SELECT role, content, timestamp FROM messages WHERE session_id = %s ORDER BY timestamp ASC', (self.session_id,))
                messages = cursor.fetchall()
                self.chat_history = {"messages": [{"role": role, "content": content, "timestamp": timestamp} for role, content, timestamp in messages]}
                cursor.execute('SELECT trim_count FROM sessions WHERE session_id = %s', (self.session_id,))
                self.trim_count = cursor.fetchone()[0]
        except Exception as e:
            print(f"Error loading chat history: {e}")
        finally:
            await self._release_connection(conn)
        return self.chat_history

    async def get_conversation(self) -> list:
        history = self.chat_history if self.session_id else await self._load_chat_history()
        messages: list = history.get("messages", [])
        return messages
    async def clear_history(self):
        await self._check_connection()
        if self.session_id is None:
            return
        conn = await self._get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute('DELETE FROM messages WHERE session_id = %s', (self.session_id,))
                conn.commit()
        except Exception as e:
            print(f"Error clearing history: {e}")
            conn.rollback()
        finally:
            await self._release_connection(conn)
        self.session_id = None
        self.chat_history = {"messages": [], "commands": []}

    async def save_chat_message(self, role: str, content: str, timestamp: str = None):
        await self._check_connection()
        if self.session_id is None:
            await self.new_conversation()
        if timestamp is None:
            timestamp = datetime.now().isoformat()
        conn = await self._get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute('INSERT INTO messages (session_id, role, content, timestamp) VALUES (%s, %s, %s, %s)', (self.session_id, role, content, timestamp))
                conn.commit()
            self.chat_history["messages"].append({"role": role, "content": content, "timestamp": timestamp})
        except Exception as e:
            print(f"Error saving chat message: {e}")
            conn.rollback()
        finally:
            await self._release_connection(conn)
        
        # Summarize after every 5 user messages if summary is "New conversation"
        user_messages = [msg for msg in self.chat_history["messages"] if msg["role"] == "user"]
        if len(user_messages) >= 5:
            await self.summarize_session()

        # Trim chat history if it exceeds 900K tokens
        #await self._trim_chat_history()

    async def save_command_execution(self, command: str, output: str):
        await self.save_chat_message("command", f"Command: {command}\nOutput: {output}")
    async def summarize_session(self):
        """
        Summarizes the session using either AI model or fallback methods.
        Handles different resource constraints and maintains database consistency.
        """
        await self._check_connection()
        if self.session_id is None:
            return

        conn = await self._get_connection()
        try:
            # Check if already summarized
            with conn.cursor() as cursor:
                cursor.execute('SELECT summary FROM sessions WHERE session_id = %s', (self.session_id,))
                existing_summary = cursor.fetchone()
                if existing_summary and existing_summary[0] != "New conversation":
                    return

            # Get relevant messages
            all_messages = self.chat_history.get("messages", [])
            if not all_messages or len(all_messages) < 3:  # Require at least 3 message exchanges
                return

            # Prepare conversation context
            conversation_text = await self._prepare_conversation_context(all_messages)

            # Try AI summarization first
            summary = await self._try_ai_summarization(conversation_text)

            # Fallback to basic summarization if AI fails
            if not summary:
                summary = await self._basic_summarization(conversation_text)

            # Validate and clean summary
            summary = await self._validate_and_clean_summary(summary)

            # Update database
            with conn.cursor() as cursor:
                cursor.execute('UPDATE sessions SET summary = %s WHERE session_id = %s', 
                             (summary, self.session_id))
                conn.commit()

        except Exception as e:
            print(f"Error summarizing session: {e}")
            conn.rollback()
        finally:
            await self._release_connection(conn)

    async def _prepare_conversation_context(self, messages):
        """Prepares conversation context for summarization."""
        # Filter out system messages and concatenate user-assistant exchanges
        relevant_messages = [
            msg for msg in messages 
            if msg["role"] in ("user", "assistant") 
            and not msg.get("content", "").startswith("Command output:")
        ]

        # Take most recent messages but limit total length
        char_limit = 2000  # Adjust based on model constraints
        conversation = []
        char_count = 0

        for msg in reversed(relevant_messages):
            content = msg.get("content", "").strip()
            if char_count + len(content) > char_limit:
                break
            conversation.insert(0, f"{msg['role'].upper()}: {content}")
            char_count += len(content)

        return "\n".join(conversation)


    async def _basic_summarization(self, text):
        """Fallback summarization method using basic NLP."""
        try:

            # Ensure required NLTK data is available
            try:
                nltk.data.find('tokenizers/punkt')
                nltk.data.find('corpora/stopwords')
            except LookupError:
                nltk.download('punkt')
                nltk.download('stopwords')

            # Tokenize and clean text
            sentences = sent_tokenize(text)
            words = word_tokenize(" ".join(sentences[:3]))
            stop_words = set(stopwords.words('english'))

            # Filter words and get most frequent
            words = [word.lower() for word in words 
                if word.isalnum() and word.lower() not in stop_words]
        
            # Get most frequent words
            freq_dist = FreqDist(words)
            important_words = [word for word, _ in freq_dist.most_common(6)]
        
            return " ".join(important_words[:6])

        except Exception as e:
            print(f"Basic summarization failed: {e}")
            return "Conversation about " + text.split()[0]

    async def _validate_and_clean_summary(self, summary):
        """Validates and cleans the generated summary."""
        if not summary:
            return "New conversation"

        # Clean the summary
        summary = " ".join(summary.split())  # Normalize whitespace
        summary = summary.strip('."')  # Remove trailing periods and quotes

        # Ensure length constraints
        words = summary.split()
        if len(words) > 6:
            summary = " ".join(words[:6])

        # Ensure it's not too short
        if len(summary) < 3:
            return "New conversation"

        return summary
    async def get_summary(self):
        await self._check_connection()
        if self.session_id is None:
            return ""
        conn = await self._get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute('SELECT summary FROM sessions WHERE session_id = %s', (self.session_id,))
                summary = cursor.fetchone()
                return summary[0] if summary else ""
        except Exception as e:
            print(f"Error getting summary: {e}")
        finally:
            await self._release_connection(conn)

    async def save_history_to_db(self):
        await self._check_connection()
        if self.session_id is None:
            return
        await self.summarize_session()
        print(f"Chat history saved to database for session {self.session_id}")

    async def session_exists(self, session_id):
        await self._check_connection()
        conn = await self._get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute('SELECT session_id FROM sessions WHERE session_id = %s', (session_id,))
                return cursor.fetchone() is not None
        except Exception as e:
            print(f"Error checking if session exists: {e}")
        finally:
            await self._release_connection(conn)

    async def load_session(self, session_id):
        await self._check_connection()
        if self.session_id != session_id:
            self.session_id = session_id
            await self._load_chat_history()
        return self.chat_history

    async def load_last_conversation(self):
        await self._check_connection()
        conn = await self._get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute('SELECT session_id FROM sessions ORDER BY timestamp DESC LIMIT 1')
                result = cursor.fetchone()
                if result:
                    self.session_id = result[0]
                    await self._load_chat_history()
                else:
                    self.new_conversation()
        except Exception as e:
            print(f"Failed to load last conversation: {e}")
            await self.new_conversation()
        finally:
            await self._release_connection(conn)

    async def _trim_chat_history(self):
        """
        Trim the chat history to ensure it does not exceed 900K tokens.
        Keep the most recent 500K tokens.
        """
        total_tokens = sum(len(word_tokenize(msg["content"])) for msg in self.chat_history["messages"])
        if total_tokens > 900000:
            trimmed_tokens = 0
            trimmed_messages = []
            for msg in reversed(self.chat_history["messages"]):
                trimmed_tokens += len(word_tokenize(msg["content"]))
                trimmed_messages.append(msg)
                if trimmed_tokens >= 500000:
                    break
            self.chat_history["messages"] = list(reversed(trimmed_messages))
            self.trim_count += 1
            await self._save_trimmed_history_to_db()

    async def _save_trimmed_history_to_db(self):
        """
        Save the trimmed chat history to the database.
        """
        await self._check_connection()
        conn = await self._get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute('DELETE FROM messages WHERE session_id = %s', (self.session_id,))
                for msg in self.chat_history["messages"]:
                    cursor.execute('INSERT INTO messages (session_id, role, content, timestamp) VALUES (%s, %s, %s, %s)', (self.session_id, msg["role"], msg["content"], msg["timestamp"]))
                cursor.execute('UPDATE sessions SET trim_count = %s WHERE session_id = %s', (self.trim_count, self.session_id))
                conn.commit()
        except Exception as e:
            print(f"Error saving trimmed chat history: {e}")
            conn.rollback()
        finally:
            await self._release_connection(conn)

    async def get_trim_count(self, session_id):
        """
        Get the trim count for a given session ID.
        If the session ID matches the current session ID, return the internal trim count.
        Otherwise, query the database for the trim count.
        """
        if self.session_id == session_id:
            return self.trim_count
        else:
            await self._check_connection()
            conn = await self._get_connection()
            try:
                with conn.cursor() as cursor:
                    cursor.execute('SELECT trim_count FROM sessions WHERE session_id = %s', (session_id,))
                    result = cursor.fetchone()
                    return result[0] if result else 0
            except Exception as e:
                print(f"Error getting trim count: {e}")
                return 0
            finally:
                await self._release_connection(conn)

    async def _try_ai_summarization(self, text):
        """Attempts to summarize using local AI model with custom cache path."""
        try:
            # Set custom cache directory
            os.environ['TRANSFORMERS_CACHE'] = '/app-data/.cache'
            os.environ['HF_HOME'] = '/app-data/.cache'

            # Ensure cache directory exists
            os.makedirs('/app-data/.cache', exist_ok=True)

            # Initialize model and tokenizer if not already loaded
            if not hasattr(self, 'summarizer'):
               # Use t5-small for lower memory usage (around 250MB)
                model_name = "t5-small"

               # MAutoModelForSeq2SeqLMCreate summarization pipeline
                self.summarizer = pipeline(
                   'summarization',
                    model=self.model,
                    tokenizer=self.tokenizer,
                    device=-1  # Use CPU
                )

           # Prepare prompt
            prompt = (
               f"{text}"
            )
            try:
                print("Trying to summarize text...")
                summary = self.summarizer(
                    prompt,
                    max_length=10,  # Approximately 6 words
                    min_length=6,   # At least a few words
                    do_sample=True,
                    temperature=0.8,
                    num_beams=2
                )[0]['summary_text']
                print(f"AI summarization succeeded: {summary}")
            except Exception as e:
                print(f"AI summarization failed: {e}")
                summary = None

           # Clean and limit summary
            summary = summary.strip()
            return summary if len(summary.split()) <= 6 else ' '.join(summary.split()[:6])

        except Exception as e:
           print(f"Local AI summarization failed: {e}")
           return None