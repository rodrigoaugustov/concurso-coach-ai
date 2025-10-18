import google.generativeai as genai
from .settings import settings
from app.contests.ai_schemas import EdictExtractionResponse

# Configura a API do Gemini com a chave do nosso settings
genai.configure(api_key=settings.GEMINI_API_KEY)

def extract_edict_data_from_pdf(pdf_content: bytes, prompt: str) -> str:
    """
    Envia um PDF para a API do Gemini como dados inline e solicita a extração 
    de dados.

    Args:
        pdf_content: O conteúdo do arquivo PDF em bytes.
        prompt: O prompt de instrução para a IA.

    Returns:
        Uma string contendo a resposta da IA (espera-se que seja um JSON).
    """
    try:
        print("AI Service: Preparando dados inline para o modelo Gemini...")
        
        # Instancia o modelo generativo
        model = genai.GenerativeModel('gemini-2.5-flash')

        # representando a "Part" do arquivo. A biblioteca o converte internamente.
        pdf_part = {
            "mime_type": "application/pdf",
            "data": pdf_content
        }

        generation_config = genai.GenerationConfig(
            response_mime_type="application/json",
            response_schema=EdictExtractionResponse,
        )
        
        print("AI Service: Enviando prompt e PDF inline para o modelo...")
        response = model.generate_content([prompt, pdf_part], generation_config=generation_config)
        print("AI Service: Resposta recebida do modelo.")
        
        return response.text

    except Exception as e:
        print(f"ERRO no AI Service: {e}")
        raise e