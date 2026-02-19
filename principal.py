import os
import stripe
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse
import pandas as pd
from io import BytesIO
from motor import executar_calculo_tb, rename_columns

app = FastAPI()

# Configuração Stripe
stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "")
EMAIL_ADMIN = "abielgm@icloud.com"

@app.get("/", response_class=HTMLResponse)
async def interface():
    # Buscamos as chaves das Variáveis de Ambiente do Render
    # Com o Fallback (reserva) caso o Render demore a propagar
    s_url = os.getenv("SUPABASE_URL", "https://iuhtopexunirguxmjiey.supabase.co")
    s_key = os.getenv("SUPABASE_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Iml1aHRvcGV4dW5pcmd1eG1qaWV5Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzE1MjIzNTcsImV4cCI6MjA4NzA5ODM1N30.EjDui9gQ5AlRaNpoVQisGUoXmK3j74gwzq9QSguxq78")

    return f"""
    <!DOCTYPE html>
    <html lang="pt-br">
    <head>
        <meta charset="UTF-8">
        <title>EstimaTB Pro</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <script src="https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2"></script>
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
        <style> .animate-in {{ animation: fadeIn 0.5s ease-out; }} @keyframes fadeIn {{ from {{ opacity: 0; transform: translateY(10px); }} to {{ opacity: 1; transform: translateY(0); }} }} </style>
    </head>
    <body class="bg-gray-100 font-sans min-h-screen flex items-center justify-center p-4">
        <div class="max-w-md w-full animate-in">
            
            <!-- SEÇÃO DE LOGIN -->
            <div id="login-section" class="bg-white p-8 rounded-[2rem] shadow-2xl border border-gray-100">
                <div class="text-center mb-8">
                    <h1 class="text-4xl font-black text-green-700 italic underline decoration-yellow-400">EstimaTB🌿</h1>
                    <p class="text-gray-400 text-[10px] font-bold uppercase mt-2 tracking-widest">Análise de Temperatura Basal</p>
                </div>

                <div class="space-y-4">
                    <input type="email" id="email" placeholder="E-mail Acadêmico" class="w-full bg-gray-50 border-2 border-gray-100 p-4 rounded-2xl focus:border-green-500 outline-none transition-all">
                    
                    <div class="relative">
                        <input type="password" id="password" placeholder="Senha" class="w-full bg-gray-50 border-2 border-gray-100 p-4 rounded-2xl focus:border-green-500 outline-none transition-all">
                        <button onclick="togglePassword('password')" class="absolute right-4 top-5 text-gray-300 hover:text-green-500">
                            <i class="fas fa-eye" id="eye-icon"></i>
                        </button>
                    </div>

                    <div id="confirm-box" class="hidden transition-all">
                        <input type="password" id="confirmPassword" placeholder="Confirme a Senha" class="w-full bg-gray-50 border-2 border-gray-100 p-4 rounded-2xl focus:border-green-500 outline-none transition-all">
                    </div>

                    <button id="btnAuth" onclick="handleAuth()" class="w-full bg-green-600 text-white py-4 rounded-2xl font-black text-lg shadow-lg hover:bg-green-700 active:scale-95 transition-all uppercase">Entrar</button>
                    
                    <button onclick="toggleMode()" id="btnSwitch" class="w-full text-green-700 font-bold text-xs uppercase tracking-tighter">Criar Nova Conta Acadêmica</button>
                </div>
            </div>

            <!-- DASHBOARD DO PESQUISADOR -->
            <div id="main-section" class="hidden animate-in">
                <div class="bg-white p-8 rounded-[2rem] shadow-2xl border-b-[12px] border-green-600 mb-6">
                    <div class="flex justify-between items-center mb-6 border-b pb-4">
                        <div class="flex flex-col text-left">
                            <span class="text-[9px] font-black text-gray-300 uppercase tracking-widest">Autenticado</span>
                            <span id="user-display" class="font-bold text-gray-700 text-sm">--</span>
                        </div>
                        <button onclick="logout()" class="text-red-500 font-black text-[10px] border-2 border-red-500 px-3 py-1 rounded-full hover:bg-red-500 hover:text-white transition-all uppercase">Sair</button>
                    </div>

                    <label class="block text-center text-xs font-black text-gray-400 uppercase mb-4 tracking-tighter italic">Importar Dados (CSV/XLSX)</label>
                    <input type="file" id="arquivo" class="block w-full text-sm mb-8 bg-gray-50 p-4 border-2 border-dashed border-gray-100 rounded-3xl cursor-pointer">
                    
                    <button id="btnCalc" onclick="calcular()" class="w-full bg-green-600 text-white py-5 rounded-[1.5rem] font-black text-xl shadow-xl hover:scale-105 transition-all uppercase">Analisar Campo</button>
                </div>

                <!-- ÁREA DE RESULTADOS -->
                <div id="resultado" class="hidden bg-white p-8 rounded-[2rem] shadow-2xl border-t-[10px] border-blue-600 transition-all scale-100">
                    <h3 class="font-black text-center text-xl mb-6 text-gray-800 tracking-tighter italic border-b pb-4">RESULTADOS DA MODELAGEM</h3>
                    <div class="grid grid-cols-2 gap-4 mb-8">
                        <div class="bg-green-50 p-6 rounded-[1.5rem] text-center shadow-inner border border-green-100">
                            <p class="text-[9px] font-black text-green-800 uppercase block mb-1">Temperatura Basal (Tb)</p>
                            <p id="res_tb" class="text-3xl font-black text-green-700 tracking-tighter">--</p>
                        </div>
                        <div class="bg-blue-50 p-6 rounded-[1.5rem] text-center shadow-inner border border-blue-100">
                            <p class="text-[9px] font-black text-blue-800 uppercase block mb-1">Precisão do Modelo (R²)</p>
                            <p id="res_r2" class="text-3xl font-black text-blue-700 tracking-tighter">--</p>
                        </div>
                    </div>
                    
                    <div id="paywall" class="p-6 bg-yellow-50 rounded-2xl text-center border-2 border-yellow-100 shadow-md">
                        <p class="text-xs text-yellow-800 font-black mb-4 uppercase italic">Liberar download dos arquivos de saída (.xlsx)?</p>
                        <button onclick="pagar()" class="bg-yellow-600 text-white px-8 py-3 rounded-full font-black text-md shadow-lg hover:bg-yellow-700 transform hover:scale-105 transition-all uppercase">Comprar Licença de Relatório</button>
                    </div>
                </div>
            </div>

        </div>

        <script>
            // CONFIGURAÇÃO SUPABASE
            const sUrl = "{s_url}";
            const sKey = "{s_key}";
            const _supabase = supabase.createClient(sUrl, sKey);
            const ADMIN_EMAIL = "{EMAIL_ADMIN}".toLowerCase();
            let mode = 'login';

            function togglePassword(id) {{
                const input = document.getElementById(id);
                const eye = document.getElementById('eye-icon');
                if (input.type === "password") {{
                    input.type = "text";
                    eye.classList.replace('fa-eye', 'fa-eye-slash');
                }} else {{
                    input.type = "password";
                    eye.classList.replace('fa-eye-slash', 'fa-eye');
                }}
            }}

            function toggleMode() {{
                mode = mode === 'login' ? 'signup' : 'login';
                document.getElementById('confirm-box').classList.toggle('hidden');
                document.getElementById('btnAuth').innerText = mode === 'login' ? 'Entrar' : 'Confirmar Cadastro';
                document.getElementById('btnSwitch').innerText = mode === 'login' ? 'Criar Nova Conta Acadêmica' : 'Voltar para o Login';
            }}

            async function handleAuth() {{
                const email = document.getElementById('email').value;
                const password = document.getElementById('password').value;
                const confirmPassword = document.getElementById('confirmPassword').value;

                if (!email || !password) return alert("Por favor, preencha os dados de acesso.");
                if (mode === 'signup' && password !== confirmPassword) return alert("As senhas não conferem!");

                const btn = document.getElementById('btnAuth');
                btn.innerText = "PROCESSANDO...";
                btn.disabled = true;

                try {{
                    let result;
                    if (mode === 'login') {{
                        result = await _supabase.auth.signInWithPassword({{ email, password }});
                    }} else {{
                        result = await _supabase.auth.signUp({{ email, password }});
                        if (!result.error) alert("Conta criada com sucesso! Você já pode logar.");
                    }}

                    if (result.error) throw result.error;
                    if (mode === 'login') location.reload();
                    
                }} catch (e) {{
                    alert("Atenção: " + e.message);
                }} finally {{
                    btn.innerText = mode === 'login' ? 'Entrar' : 'Confirmar Cadastro';
                    btn.disabled = false;
                }}
            }}

            async function checkUser() {{
                const {{ data: {{ user }} }} = await _supabase.auth.getUser();
                if (user) {{
                    document.getElementById('login-section').classList.add('hidden');
                    document.getElementById('main-section').classList.remove('hidden');
                    document.getElementById('user-display').innerText = user.email.toLowerCase();
                    
                    if (user.email.toLowerCase() === ADMIN_EMAIL) {{
                        document.getElementById('paywall').innerHTML = '<div class="bg-green-100 text-green-800 p-3 rounded-xl border border-green-200 font-black italic tracking-widest uppercase text-[10px]">✓ Administrador Master Reconhecido</div>';
                    }}
                }}
            }}
            checkUser();

            async function logout() {{
                await _supabase.auth.signOut();
                location.reload();
            }}

            async function calcular() {{
                const file = document.getElementById('arquivo').files[0];
                if(!file) return alert("Anexe um arquivo primeiro.");
                const btn = document.getElementById('btnCalc');
                btn.innerText = "CALCULANDO...";
                const fd = new FormData();
                fd.append('file', file);

                try {{
                    const r = await fetch('/analisar', {{ method: 'POST', body: fd }});
                    const d = await r.json();
                    document.getElementById('resultado').classList.remove('hidden');
                    document.getElementById('res_tb').innerText = d.tb_estimada + " °C";
                    document.getElementById('res_r2').innerText = d.r2.toFixed(4);
                    window.scrollTo({{ top: document.body.scrollHeight, behavior: 'smooth' }});
                }} catch(e) {{
                    alert("Erro técnico na análise de regressão.");
                }} finally {{
                    btn.innerText = "Analisar Campo";
                }}
            }}

            async function pagar() {{
                const r = await fetch('/checkout-stripe');
                const d = await r.json();
                window.location.href = d.url;
            }}
        </script>
    </body>
    </html>
    """

# Funções Analisar e Stripe sem alterações (mantendo chaves Python seguras)
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
        return {"tb_estimada": round(resultado['melhor_resultado']['Temperatura (ºC)'], 2), "r2": resultado['melhor_resultado']['R2']}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/checkout-stripe")
def criar_checkout():
    session = stripe.checkout.Session.create(
        payment_method_types=['card', 'pix'],
        line_items=[{'price_data': {'currency': 'brl', 'product_data': {'name': 'Licença EstimaTB Pro'}, 'unit_amount': 2990}, 'quantity': 1}],
        mode='payment',
        success_url='https://temperatura-basal.onrender.com', cancel_url='https://temperatura-basal.onrender.com',
    )
    return {"url": session.url}
