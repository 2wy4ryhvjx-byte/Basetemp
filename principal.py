import os
import stripe
from fastapi import FastAPI, UploadFile, File, HTTPException, Request
from fastapi.responses import HTMLResponse
from supabase import create_client, Client
import pandas as pd
from io import BytesIO
from motor import executar_calculo_tb, rename_columns

app = FastAPI()

# Configurações de API (Pegando do Render Env Vars)
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_KEY")

# Só cria o cliente se as chaves existirem para evitar erro no build
if supabase_url and supabase_key:
    supabase: Client = create_client(supabase_url, supabase_key)
else:
    print("AVISO: Chaves do Supabase não encontradas!")

# Seu e-mail pessoal
EMAIL_ADMIN = "abielgm@icloud.com" 

@app.get("/", response_class=HTMLResponse)
async def interface():
    # Usamos chaves duplas {{ }} para o JavaScript dentro do f-string do Python
    return f"""
    <!DOCTYPE html>
    <html lang="pt-br">
    <head>
        <meta charset="UTF-8"><title>EstimaTB Pro - Login</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <script src="https://unpkg.com/@supabase/supabase-js@2"></script>
    </head>
    <body class="bg-gray-100 font-sans">
        <div id="app" class="max-w-2xl mx-auto py-12 px-4">
            <!-- TELA DE LOGIN -->
            <div id="login-section" class="bg-white p-8 rounded-xl shadow-md text-center">
                <h1 class="text-3xl font-bold text-green-700 mb-6 font-mono">EstimaTB 🌿</h1>
                <input type="email" id="email" placeholder="Seu e-mail" class="w-full border p-2 mb-4 rounded">
                <input type="password" id="password" placeholder="Sua senha" class="w-full border p-2 mb-4 rounded">
                <div class="flex gap-2">
                    <button onclick="auth('login')" class="w-1/2 bg-green-600 text-white py-2 rounded font-bold">Entrar</button>
                    <button onclick="auth('signup')" class="w-1/2 border border-green-600 text-green-600 py-2 rounded font-bold">Cadastrar</button>
                </div>
            </div>

            <!-- TELA DO CALCULADOR (Escondida) -->
            <div id="main-section" class="hidden">
                <div class="bg-white p-8 rounded-xl shadow-md mb-8">
                    <div class="flex justify-between items-center mb-6 border-b pb-4">
                        <h2 class="text-xl font-bold text-green-700 uppercase">Acesso: <span id="user-display"></span></h2>
                        <button onclick="logout()" class="text-red-500 font-bold hover:underline">Sair</button>
                    </div>
                    
                    <label class="block mb-2 text-sm text-gray-600 font-bold italic">Selecione o arquivo meteorológico:</label>
                    <input type="file" id="arquivo" class="block w-full text-sm mb-6 border p-2 rounded bg-gray-50">
                    <button id="btn" onclick="calcular()" class="w-full bg-green-600 text-white py-4 rounded-xl font-bold text-lg shadow-lg hover:bg-green-700 transition-all">ANALISAR DADOS</button>
                </div>

                <div id="resultado" class="hidden bg-white p-8 rounded-xl shadow-md border-t-8 border-green-600 animate-bounce-short">
                    <h3 class="font-black text-center text-xl mb-6 text-gray-800 border-b pb-2">RESULTADOS ENCONTRADOS</h3>
                    <div class="grid grid-cols-2 gap-4 mb-6">
                        <div class="bg-green-50 p-4 rounded-xl text-center shadow-inner">
                            <p class="text-xs text-green-800 font-bold uppercase mb-1">Temperatura Basal (Tb)</p>
                            <p id="res_tb" class="text-3xl font-black text-green-600 font-mono">--</p>
                        </div>
                        <div class="bg-blue-50 p-4 rounded-xl text-center shadow-inner">
                            <p class="text-xs text-blue-800 font-bold uppercase mb-1">Precisão (R²)</p>
                            <p id="res_r2" class="text-3xl font-black text-blue-600 font-mono">--</p>
                        </div>
                    </div>
                    
                    <div id="paywall" class="p-6 bg-yellow-50 rounded-xl text-center border-2 border-yellow-200 shadow-lg">
                        <p class="mb-4 text-yellow-800 font-medium">Estudante, deseja o relatório Excel detalhado pronto para sua tese?</p>
                        <button onclick="pagar()" class="bg-yellow-600 text-white px-8 py-3 rounded-full font-black hover:bg-yellow-700 transform hover:scale-105 transition-all">OBTER RELATÓRIO COMPLETO (STa)</button>
                    </div>
                </div>
            </div>
        </div>

        <script>
            const supabaseUrl = '{supabase_url}';
            const supabaseKey = '{supabase_key}';
            const _supabase = supabase.createClient(supabaseUrl, supabaseKey);
            const ADMIN_EMAIL = "{EMAIL_ADMIN}";

            async function auth(type) {{
                const email = document.getElementById('email').value;
                const password = document.getElementById('password').value;
                if(!email || !password) return alert("Preencha e-mail e senha.");
                
                let res;
                if(type === 'login') res = await _supabase.auth.signInWithPassword({{ email, password }});
                else res = await _supabase.auth.signUp({{ email, password }});
                
                if(res.error) alert(res.error.message);
                else location.reload();
            }}

            async function logout() {{
                await _supabase.auth.signOut();
                location.reload();
            }}

            async function checkUser() {{
                const {{ data: {{ user }} }} = await _supabase.auth.getUser();
                if (user) {{
                    document.getElementById('login-section').classList.add('hidden');
                    document.getElementById('main-section').classList.remove('hidden');
                    document.getElementById('user-display').innerText = user.email;
                    
                    if(user.email.toLowerCase() === ADMIN_EMAIL.toLowerCase()) {{
                        document.getElementById('paywall').innerHTML = '<div class="p-2 bg-green-100 text-green-800 rounded font-black border border-green-300 italic">⭐ MODO ADMIN ATIVADO: TODOS OS RELATÓRIOS ESTÃO LIBERADOS!</div>';
                    }}
                }}
            }}
            checkUser();

            async function calcular() {{
                const btn = document.getElementById('btn');
                const file = document.getElementById('arquivo').files[0];
                if(!file) return alert("Por favor, selecione um arquivo antes.");
                
                btn.innerText = "EXECUTANDO MOTOR CIENTÍFICO...";
                btn.disabled = true;

                const fd = new FormData();
                fd.append('file', file);
                
                try {{
                    const response = await fetch('/analisar', {{ method: 'POST', body: fd }});
                    const data = await response.json();
                    
                    if(data.tb_estimada !== undefined) {{
                        document.getElementById('resultado').classList.remove('hidden');
                        document.getElementById('res_tb').innerText = data.tb_estimada + " ºC";
                        document.getElementById('res_r2').innerText = data.r2.toFixed(3);
                        window.scrollTo({{ top: document.body.scrollHeight, behavior: 'smooth' }});
                    }}
                }} catch(e) {{
                    alert("Erro ao processar arquivo. Verifique o formato.");
                }} finally {{
                    btn.innerText = "ANALISAR DADOS";
                    btn.disabled = false;
                }}
            }}

            async function pagar() {{
                const res = await fetch('/checkout-stripe');
                const data = await res.json();
                window.location.href = data.url;
            }}
        </script>
    </body>
    </html>
    """

# ROTAS ABAIXO FORA DO F-STRING (Chaves simples aqui)

@app.post("/analisar")
async def analisar_dados(file: UploadFile = File(...)):
    content = await file.read()
    try:
        if file.filename.endswith('.csv'):
            df = pd.read_csv(BytesIO(content), sep=None, engine='python')
        else:
            df = pd.read_excel(BytesIO(content))

        df = rename_columns(df)
        df['Data'] = pd.to_datetime(df['Data'], errors='coerce')
        resultado = executar_calculo_tb(df, 0, 20, 0.5)

        return {
            "tb_estimada": resultado['melhor_resultado']['Temperatura (ºC)'], 
            "r2": resultado['melhor_resultado']['R2']
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/checkout-stripe")
def criar_checkout():
    session = stripe.checkout.Session.create(
        payment_method_types=['card', 'pix'],
        line_items=[{
            'price_data': {
                'currency': 'brl', 
                'product_data': {'name': 'EstimaTB Pro - Relatório Completo'}, 
                'unit_amount': 2500
            }, 
            'quantity': 1
        }],
        mode='payment',
        success_url='https://temperatura-basal.onrender.com', 
        cancel_url='https://temperatura-basal.onrender.com',
    )
    return {"url": session.url}
