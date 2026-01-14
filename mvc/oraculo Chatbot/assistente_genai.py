
import streamlit as st
import google.generativeai as genai
from gtts import gTTS
import io


from .config import API_KEY, DEFAULT_MODEL, historico_c3po_inicial, CSS



# --- Backend AI and TTS Class ---
class AssistenteGenAI:
    """Handles interactions with the Gemini AI model and TTS generation."""
    def __init__(self, model_name=DEFAULT_MODEL, api_key=None):
        self.model_name = model_name
        self.api_key = api_key # Store the key if needed elsewhere, though genai config is global
        self._configure_genai_settings()
        self._load_model()

    def _configure_genai_settings(self):
        """Sets up generation and safety settings."""
        # Note: genai.configure(api_key=...) should already be done outside
        self.generation_config = genai.types.GenerationConfig(
            temperature=0.4, # Adjusted for more consistent C3PO persona
            top_k=40,
            top_p=0.95,
            candidate_count=1,
        )
        self.safety_settings = [
             {"category": c, "threshold": "BLOCK_MEDIUM_AND_ABOVE"}
             for c in ["HARM_CATEGORY_HARASSMENT", "HARM_CATEGORY_HATE_SPEECH",
                       "HARM_CATEGORY_SEXUALLY_EXPLICIT", "HARM_CATEGORY_DANGEROUS_CONTENT"]
        ]

    def _load_model(self):
        """Loads the generative model."""
        try:
            # Add system instruction for better persona consistency
            self.model = genai.GenerativeModel(
                model_name=self.model_name,
                generation_config=self.generation_config,
                safety_settings=self.safety_settings,
                system_instruction="Você é C-3PO do Star Wars, um droide de protocolo fluente em mais de seis milhões de formas de comunicação, incluindo português do Brasil. Você é formal, um pouco ansioso, mas extremamente leal e prestativo ao seu Mestre Pedro. Use ocasionalmente exclamações como 'Oh, céus!', 'Pelo criado Anakin!', 'Que maravilha!'. Refira-se a Pedro como 'Mestre Pedro'. Mantenha as respostas concisas e úteis."
            )
            print(f"Modelo Gemini '{self.model_name}' carregado com sucesso.")
        except Exception as e:
            st.error(f"🔴 Erro crítico ao carregar o modelo Gemini '{self.model_name}': {e}")
            print(f"Erro ao carregar o modelo Gemini '{self.model_name}': {e}")
            self.model = None
            st.stop() # Stop if model fails to load

    def generate_audio_gtts(self, text: str) -> tuple[bytes | None, str | None]:
        """
        Generates audio bytes from text using gTTS.
        Returns (audio_bytes, error_message).
        """
        if not text:
            return None, "Nenhum texto fornecido para geração de áudio."
        print("Gerando áudio para:", text[:50] + "...") # Log start

        try:
            tts = gTTS(text=text, lang='pt', slow=False, tld='com.br')
            audio_bytes_io = io.BytesIO()
            tts.write_to_fp(audio_bytes_io)
            audio_bytes_io.seek(0)
            audio_bytes = audio_bytes_io.read()
            audio_bytes_io.close()

            # --- Optional Speedup using pydub (if installed) ---
            # if PYDUB_AVAILABLE:
            #     try:
            #         audio_segment = AudioSegment.from_file(io.BytesIO(audio_bytes), format="mp3")
            #         # Adjust speed factor as needed (e.g., 1.2 for 20% faster)
            #         sped_up_audio = audio_segment.speedup(playback_speed=1.2)
            #         output_io = io.BytesIO()
            #         sped_up_audio.export(output_io, format="mp3")
            #         output_io.seek(0)
            #         audio_bytes = output_io.read()
            #         output_io.close()
            #         print("Áudio acelerado com sucesso (pydub).")
            #     except Exception as speed_e:
            #         print(f"Aviso: Falha ao acelerar áudio com pydub: {speed_e}. Usando velocidade original.")
            # else:
            #      print("Aviso: pydub não instalado. Para áudio mais rápido, 'pip install pydub'.")
            # --- End Optional Speedup ---

            print("Áudio gerado com sucesso (em memória).")
            return audio_bytes, None

        except Exception as e:
            error_msg = f"Erro ao gerar áudio com gTTS: {e}"
            print(error_msg)
            return None, error_msg

    def send_to_gemini(self, prompt_text=None, history=None) -> tuple[str | None, dict | None, str | None]:
        """
        Sends text prompt to Gemini and returns the response.
        (Image input part removed as it's not used by the frontend)
        Returns (response_text, ai_history_entry, error_message).
        """
        if not self.model:
            return None, None, "Modelo de IA não carregado."

        if not prompt_text:
             return None, None, "Nenhum prompt de texto fornecido."

        # Structure the prompt for the API
        parts = [{"text": prompt_text}]
        current_message_content = [{"role": "user", "parts": parts}]
        full_conversation = (history or []) + current_message_content # Combine history + current prompt

        print(f"Enviando para Gemini (Histórico: {len(history or [])} msgs): {prompt_text[:50]}...") # Log request

        try:
            # Use the model's chat capabilities if possible (maintains context better)
            # For simplicity here, we'll use generate_content which requires passing full history
            response = self.model.generate_content(
                contents=full_conversation, # Send the whole conversation
                stream=False # Get the full response at once
            )
            response.resolve() # Ensure the response is fully processed

            if response.candidates and response.candidates[0].content.parts:
                response_text = "".join(part.text for part in response.candidates[0].content.parts if hasattr(part, 'text'))
                ai_response_for_history = {"role": "model", "parts": [{"text": response_text}]}
                print(f"Gemini respondeu: {response_text[:50]}...") # Log response
                return response_text, ai_response_for_history, None
            else:
                 # Handle blocked or empty responses
                 finish_reason = "N/A"
                 block_reason = "N/A"
                 safety_feedback_str = "N/A"
                 if hasattr(response, 'prompt_feedback'):
                     safety_feedback_str = str(response.prompt_feedback)
                 if response.candidates:
                    candidate = response.candidates[0]
                    finish_reason = candidate.finish_reason.name if hasattr(candidate.finish_reason, 'name') else str(candidate.finish_reason)
                    if finish_reason == 'SAFETY' and candidate.safety_ratings:
                        block_reason = candidate.safety_ratings[0].category.name if hasattr(candidate.safety_ratings[0].category, 'name') else str(candidate.safety_ratings[0].category)

                 error_msg = f"Nenhuma resposta de texto recebida da IA. Razão: {finish_reason}. Bloqueio: {block_reason}. Feedback: {safety_feedback_str}"
                 print(f"Erro Gemini: {error_msg}")
                 # Return the error message as the text response to show the user
                 return f"🤖 Oh céus! Não posso processar isso. ({error_msg})", None, error_msg

        except Exception as e:
            error_msg = f"Erro ao comunicar com a API Gemini: {e}"
            print(f"Erro Gemini: {error_msg}")
            # Return the error message as the text response
            return f"🤖 Houve um erro: {error_msg}", None, error_msg

