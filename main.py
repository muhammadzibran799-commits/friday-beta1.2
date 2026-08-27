from fastapi import FastAPI, UploadFile, File
from pydantic import BaseModel
from groq import Groq
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware
import json
import uuid
import shutil
import pdfplumber
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

def ekstrak_teks_pdf(file_path:str)->str:
    try:
        with pdfplumber.open(file_path) as pdf :
            teks=""
            for halaman in pdf.pages:
                teks +=halaman.extract_text() or ""
                
        if not teks.strip():
            return "Tidak ada teks yang dapat diekstrak"
        
        return teks[:8000]
    
    except FileNotFoundError:
        return f"File tidak ditemukan: {file_path}"
    except Exception as e:
        return f"Error baca PDF: {str(e)}"

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
    },
    {
        "type":"function",
        "function":{
            "name": "ekstrak_teks_pdf",
            "description":"tool ini untuk mengekstrak pdf. Kamu bisa menggunakan ketika dibutuhkan misalnya, user mengirimkan pdf, atau segala hal yang berkaitan dengan pdf maka kamu perlu menggunakan tool ini.",
            "parameters": {
                "type":"object",
                "properties":{
                    "file_path":{
                        "type":"string",
                        "description":"Path lengkap ke file pdf di server, didapat dari hasil upload."
                    }
                },
                "required":["file_path"]              
            }
        }
    }
    
]

def execute_tool(tool_name:str,tool_args:dict)->str:
    if tool_name == "cari_web":
        return cari_web(**tool_args)
    
    elif tool_name == "ekstrak_teks_pdf":
        return ekstrak_teks_pdf(**tool_args)
    
    else:
        return f"Error: tool '{tool_name}' tidak dikenal"
    

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
            tool_name = tool_call.function.name
            tool_args = json.loads(tool_call.function.arguments)
            hasil = execute_tool(tool_name, tool_args)
            

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
    file_path : str | None = None 
    


@app.get("/")
def status():
    return {"status": "Friday ready to help"}

@app.post("/chat")
def chat(pesan: PesanUser):
    pesan_lengkap = pesan.pesan
    if pesan.file_path:
        pesan_lengkap += f"\n\n[INSTRUKSI: User telah mengupload file PDF. Gunakan tool ekstrak_teks_pdf dengan file_path '{pesan.file_path}' untuk membaca isinya sebelum menjawab pertanyaan user.]"
    tanya = tanya_ai(pesan_lengkap, pesan.history)
    return {'jawaban': tanya}

@app.post("/upload-pdf")
async def upload_pdf(file: UploadFile=File(...)):
    temp_path = f"/temp/{uuid.uuid4()}_{file.filename}"
    
    with open(temp_path,"wb") as f:
        shutil.copyfileobj(file.file,f)
    
    return {"file_path":temp_path}
    
    



    
    

