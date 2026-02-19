import os
import stripe
from fastapi import FastAPI, UploadFile, File, HTTPException, Request
from fastapi.responses import HTMLResponse
from supabase import create_client, Client
import pandas as pd
from io import BytesIO
from motor import executar_calculo_tb, rename_columns

app = FastAPI()

# Configurações de API (Render pegará do seu Env Vars)
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(supabase_url, supabase_key)

# Seu e-mail pessoal para o sistema te reconhecer como dono
EMAIL_ADMIN = "SEU_EMAIL_AQUI@EXEMPLO.COM" 

@app.get("/", response_class=HTMLResponse)
async def interface():
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
                <h1 class="text-3xl font-bold text-green-700 mb-6">EstimaTB 🌿</h1>
                <input type="email" id="email" placeholder="Seu e-mail" class="w-full border p-2 mb-4 rounded">
                <input type="password" id="password" placeholder="Sua senha" class="w-full border p-2 mb-4 rounded">
                <div class="flex gap-2">
                    <button onclick="auth('login')" class="w-1/2 bg-green-600 text-white py-2 rounded">Entrar</button>
                    <button onclick="auth('signup')" class="w-1/2 border border-green-600 text-green-600 py-2 rounded">Cadastrar</button>
                </div>
            </div>

            <!-- TELA DO CALCULADOR (Escondida por padrão) -->
            <div id="main-section" class="hidden">
                <div class="bg-white p-8 rounded-xl shadow-md mb-8">
                    <div class="flex justify-between items-center mb-6">
                        <h2 class="text-2xl font-bold text-green-700">Olá, <span id="user-display"></span></h2>
                        <button onclick="logout()" class="text-red-500 text-sm">Sair</button>
                    </div>
                    
                    <input type="file" id="arquivo" class="block w-full text-sm mb-4">
                    <button id="btn" onclick="calcular()" class="w-full bg-green-600 text-white py-3 rounded font-bold hover:bg-green-700">Analisar Dados</button>
                </div>

                <div id="resultado" class="hidden bg-white p-8 rounded-xl shadow-md border-t-4 border-green-500">
                    <h3 class="font-bold text-lg mb-4 text-gray-800">Resultado da Análise</h3>
                    <div class="grid grid-cols-2 gap-4 mb-6">
                        <div class="bg-gray-50 p-4 rounded text-center">
                            <p class="text-xs text-gray-500 uppercase">Tb Estimada</p>
                            <p id="res_tb" class="text-2xl font-bold text-green-600">--</p>
                        </div>
                        <div class="bg-gray-50 p-4 rounded text-center">
                            <p class="text-xs text-gray-500 uppercase">R² (Precisão)</p>
                            <p id="res_r2" class="text-2xl font-bold text-blue-600">--</p>
                        </div>
                    </div>
                    
                    <!-- BLOCO DE PAGAMENTO (Só aparece para usuários comuns) -->
                    <div id="paywall" class="p-6 bg-yellow-50 rounded-lg text-center border border-yellow-200">
                        <p class="mb-4">Para baixar o Excel completo com todos os cálculos, você precisa do acesso Pro.</p>
                        <button onclick="pagar()" class="bg-yellow-600 text-white px-6 py-2 rounded font-bold hover:bg-yellow-700">Liberar Relatório Completo</button>
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
                    
                    // Lógica especial para você (Admin)
                    if(user.email === ADMIN_EMAIL) {{
                        document.getElementById('paywall').innerHTML = '<p class="text-green-700 font-bold font-lg">✓ Acesso Admin Liberado!</p>';
                    }}
                }}
            }}
            checkUser();

            async function calcular() {{
                const btn = document.getElementById('btn');
                const file = document.getElementById('arquivo').files[0];
                if(!file) return alert("Selecione um arquivo!");
                
                btn.innerText = "Calculando...";
                const fd = new FormData();
                fd.append('file', file);
                
                const response = await fetch('/analisar', {{ method: 'POST', body: fd }});
                const data = await response.json();
                
                document.getElementById('resultado').classList.remove('hidden');
                document.getElementById('res_tb').innerText = data.tb_estimada + " ºC";
                document.getElementById('res_r2').innerText = data.r2.toFixed(3);
                btn.innerText = "Analisar Dados";
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

# (Mantenha as rotas de @app.post("/analisar") e /checkout-stripe como estavam no código anterior)
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

        return {{"tb_estimada": resultado['melhor_resultado']['Temperatura (ºC)'], "r2": resultado['melhor_resultado']['R2']}}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/checkout-stripe")
def criar_checkout():
    session = stripe.checkout.Session.create(
        payment_method_types=['card', 'pix'],
        line_items=[{{'price_data': {{'currency': 'brl', 'product_data': {{'name': 'EstimaTB Pro - Relatório'}}, 'unit_amount': 2500}}, 'quantity': 1}}],
        mode='payment',
        success_url='https://temperatura-basal.onrender.com', 
        cancel_url='https://temperatura-basal.onrender.com',
    )
    return {{"url": session.url}}
