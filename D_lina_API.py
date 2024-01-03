import ctranslate2
import sentencepiece as spm
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI()
# Supported languages
SUPPORTED_LANGUAGES = {"eng_Latn", "fra_Latn", "bam_Latn", "spa_Latn"}  # Assuming ISO codes

# Load models (adjust paths as needed)
ct_model_path = "C:\\Users\\Ari\\D_lina_API\\nllb-200_1.2B_int8_ct2\\ct2-nllb-200-distilled-1.2B-int8"
sp_model_path = "C:\\Users\\Ari\\D_lina_API\\flores200_sacrebleu_tokenizer_spm.model"
device = "cpu"  

sp = spm.SentencePieceProcessor()
sp.load(sp_model_path)

translator = ctranslate2.Translator(ct_model_path, device)

class TranslationRequest(BaseModel):
    text: str
    source_language: str
    target_language: str

@app.post("/translate")
async def translate(request: TranslationRequest):
    # Check if the requested languages are supported
    if request.source_language not in SUPPORTED_LANGUAGES or request.target_language not in SUPPORTED_LANGUAGES:
        return {"error": "One or more specified languages are not supported"}, 400

    try:
        # Subword the source sentence
        source_sentence_subworded = sp.encode_as_pieces(request.text.strip())
        source_sentence_subworded = [request.source_language] + source_sentence_subworded + ["</s>"]

        # Translation
        translation_subworded = translator.translate_batch(
            [source_sentence_subworded], 
            batch_type="tokens", 
            max_batch_size=2024, 
            beam_size=4,
            target_prefix=[[request.target_language]]
        )[0].hypotheses[0]

        if request.target_language in translation_subworded:
            translation_subworded.remove(request.target_language)

        # Desubword the target sentence
        translation = sp.decode(translation_subworded)

        return {"translated_text": translation}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)