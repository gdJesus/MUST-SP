
import streamlit as st
import google.generativeai as genai
from gtts import gTTS
import numpy as np
import matplotlib.pyplot as plt
import io


# Optional, for audio speedup if you install it later:
# try:
#     from pydub import AudioSegment
#     PYDUB_AVAILABLE = True
# except ImportError:
#     PYDUB_AVAILABLE = False


from config import API_KEY, DEFAULT_MODEL, historico_c3po_inicial, CSS

from graficos import funcao_seno, sinal_pwm, circuito_rc

from assistente_genai import AssistenteGenAI


# --- Frontend Functions ---
def ChatbotScreen(assistente: AssistenteGenAI):
    """Renders the chat interface and handles interactions."""

    st.image("https://moseisleychronicles.wordpress.com/wp-content/uploads/2015/11/untitled-215.gif", width=650)
    st.title("Assistente C3PO")
    st.caption("Seu droide de protocolo pessoal para produtividade e mais.")

    # --- Chat History Display ---
    # Use a container with specific height and scrollbar for chat history
    chat_history_container = st.container(height=500, border=False)
    with chat_history_container:
        for i, message in enumerate(st.session_state.messages):
            role = message["role"]
            # Ensure parts exist and extract text
            display_text = ""
            if "parts" in message and isinstance(message["parts"], list):
                 display_text = "".join(p.get("text", "") for p in message["parts"] if isinstance(p, dict))

            with st.chat_message(name=role, avatar="🤖" if role == "model" else "🧑‍🚀"):
                st.markdown(display_text)
                # Add TTS button only for non-empty model messages
                if role == "model" and display_text and not display_text.startswith("🤖"): # Avoid TTS for error messages starting with emoji
                    tts_button_key = f"tts_{i}_{role}" # More specific key
                    if st.button(f"🔊 Ouvir", key=tts_button_key, help="Ouvir a resposta do C3PO"):
                        with st.spinner("Gerando áudio... Por favor, aguarde."):
                            audio_bytes, error = assistente.generate_audio_gtts(display_text)
                            if error:
                                st.toast(f"Erro no TTS: {error}", icon="🚨") # Use toast for non-blocking error
                            elif audio_bytes:
                                # Store audio and rerun to display it outside the loop
                                st.session_state.current_audio_bytes = audio_bytes
                                st.session_state.current_audio_key = tts_button_key # Store key to avoid re-playing on unrelated reruns
                                st.rerun()

    # --- Audio Player ---
    # Display audio player ONLY if the corresponding button was just clicked
    # And clear it after it's presumably played or if another button is clicked
    if 'current_audio_bytes' in st.session_state and st.session_state.current_audio_bytes:
        # Check if the last button clicked corresponds to this audio (simple check)
        # A more robust way might involve checking widget state, but this is often sufficient
         if 'last_triggered_button_key' not in st.session_state or st.session_state.last_triggered_button_key == st.session_state.get('current_audio_key'):
              st.audio(st.session_state.current_audio_bytes, format='audio/mp3', start_time=0)
         # Clear the audio after displaying it once to prevent re-playing on next rerun
         st.session_state.current_audio_bytes = None
         st.session_state.current_audio_key = None


    # --- User Input ---
    user_prompt = st.chat_input("Digite sua mensagem para o C3PO:")
    if user_prompt:
        print(f"Usuário digitou: {user_prompt[:50]}...")
        # Append user message to state immediately for display
        st.session_state.messages.append({"role": "user", "parts": [{"text": user_prompt}]})
        # Clear any pending audio playback before showing spinner/getting response
        st.session_state.current_audio_bytes = None
        st.session_state.current_audio_key = None
        st.rerun() # Rerun to show user message instantly

# Separate function to handle the Gemini response after the user message is shown
def handle_gemini_response(assistente: AssistenteGenAI):
    # Check if the last message is from the user and hasn't been processed yet
    if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
        if 'last_processed_user_message' not in st.session_state or st.session_state.last_processed_user_message != st.session_state.messages[-1]:

            last_user_message = st.session_state.messages[-1]
            st.session_state.last_processed_user_message = last_user_message # Mark as being processed

            with st.spinner("C3PO está calculando a resposta..."):
                # Send history *excluding* the last user message (which is the current prompt)
                response_text, ai_history_entry, error = assistente.send_to_gemini(
                    prompt_text=last_user_message["parts"][0]["text"],
                    history=st.session_state.messages[:-1] # Pass history BEFORE the current user msg
                )

            # If Gemini returned a valid response structure, add it to history
            if ai_history_entry:
                st.session_state.messages.append(ai_history_entry)
            # If there was an error but Gemini generated an error message text
            elif response_text and not ai_history_entry:
                 st.session_state.messages.append({"role": "model", "parts": [{"text": response_text}]})
            # If there was a critical error and no text response
            elif error:
                 st.session_state.messages.append({"role": "model", "parts": [{"text": f"🤖 Oh não! Erro interno: {error}"}]})

            # Rerun to display the new AI response
            st.rerun()


# --- Main Page Function ---
def C3poChatbotPage():
    """Sets up the main page layout and logic."""
    
    st.set_page_config(page_title="C3PO Assistente", layout="wide", page_icon="🤖")

    # --- Apply CSS ---
    st.markdown(CSS, unsafe_allow_html=True)

    # --- Initialize Session State ---
    if 'messages' not in st.session_state:
        # Start with a fresh copy of the initial history
        st.session_state.messages = list(historico_c3po_inicial)
        print("Histórico de chat inicializado.")
    if 'current_audio_bytes' not in st.session_state:
        st.session_state.current_audio_bytes = None
    if 'current_audio_key' not in st.session_state:
        st.session_state.current_audio_key = None
    if 'last_processed_user_message' not in st.session_state:
        st.session_state.last_processed_user_message = None

    # --- Instantiate Assistant ---
    # Pass the configured API key (already checked at the top)
    assistente = AssistenteGenAI(api_key=API_KEY)
    if not assistente.model: # Check if model loaded successfully
         st.error("🔴 Modelo de IA não pôde ser carregado. A aplicação não pode continuar.")
         st.stop()

    # --- Page Layout ---
    col1, col2 = st.columns([2, 1]) # Chat takes more space

    with col1:
        # Render the chat screen (displays history, handles input)
        ChatbotScreen(assistente)

        # Handle the response generation *after* potential input/rerun
        handle_gemini_response(assistente)


    with col2:
        st.header("📊 Dashboard Simples")
        st.write("Visualização de dados de exemplo.")
        
        # Criação das abas
        tab1, tab2, tab3 = st.tabs(["Funções Seno e Cosseno", "Sinal PWM", "Resposta de Circuito RC"])
        with tab1:
            st.subheader("Funções Seno e Cosseno")
            funcao_seno()

        with tab2:
            st.subheader("Sinal PWM")
            sinal_pwm()

        with tab3:
            st.subheader("Resposta de Circuito RC")
            circuito_rc()

# --- Run the App ---
if __name__ == "__main__":
    C3poChatbotPage()