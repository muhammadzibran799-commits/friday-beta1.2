from fastapi import FastAPI
from pydantic import BaseModel
from groq import Groq
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware
import json
from ddgs import DDGS

load_dotenv()
client = Groq()
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# percakapan = []
# total_token = 0

def cari_web(query:str)->str:
    with DDGS() as ddgs:
        results = list(ddgs.text(query, max_results=3))
    
    if not results:
        return "Tidak ada hasil yang ditemukan."
    
    output=""
    for r in results:
        output += f"Judul: {r['title']}\nURL: {r['href']}\nRingkasan: {r['body']}\n\n"
        
    return output  
     

tools = [
    {
        "type":"function",
        "function":{
            "name": "cari_web",
            "description": "Gunakan web ketika membutuhkan informasi terkini. Ketik dibutuhkan, pastikan untuk SELALU mengisi parameter query dengan kata kunci dari pertanyaan user",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Pertanyaan yang ingin dicari di web"
                    }
                },
                "required": ["query"]
            }
        }
    }
]

def tanya_ai(pesan, history):
    try:
        percakapan_sementara = history + [{"role": "user", "content": pesan}]

        response = client.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=percakapan_sementara,
            tools=tools,
            tool_choice="auto"
        )

        message = response.choices[0].message

        if message.tool_calls:
            tool_call = message.tool_calls[0]
            argumen = json.loads(tool_call.function.arguments)
            hasil = cari_web(argumen["query"])

            percakapan_sementara.append(message)
            percakapan_sementara.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": hasil
            })

            response2 = client.chat.completions.create(
                model="openai/gpt-oss-120b",
                messages=percakapan_sementara,
                tools=tools,
                tool_choice="none"
            )

            jawaban = response2.choices[0].message.content
        else:
            jawaban = message.content

        return jawaban

    except Exception as e:
        return f"Error: {str(e)}"

class PesanUser(BaseModel):
    pesan : str
    history : list[dict]
    


@app.get("/")
def status():
    return {"status": "Friday ready to help"}

@app.post("/chat")
def chat(pesan: PesanUser):
    tanya=tanya_ai(pesan.pesan,pesan.history)
    return {'jawaban':tanya}

    
    

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

    
    

