from fastapi import FastAPI
from pydantic import BaseModel
from groq import Groq
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware


load_dotenv()
client = Groq()
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

percakapan = []
# total_token = 0

def tanya_ai(pesan):
    # global total_token
    try:
        percakapan_sementara = percakapan + [{"role": "user", "content": pesan}]
        
        completion = client.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=percakapan_sementara,
        )
        
        jawaban = completion.choices[0].message.content
        
        percakapan.append({"role": "user", "content": pesan})
        percakapan.append({"role": "assistant", "content": jawaban})

        return jawaban
    
    except Exception as e:
        mistake=f"Terjadi kesalahan: {e}\nTidak bisa melanjutkan percakapan."
        return mistake

class PesanUser(BaseModel):
    pesan : str
    


@app.get("/")
def status():
    return {"status": "Friday ready to help"}

@app.post("/chat")
def chat(pesan: PesanUser):
    tanya=tanya_ai(pesan.pesan)
    return {'jawaban':tanya}

    
    
