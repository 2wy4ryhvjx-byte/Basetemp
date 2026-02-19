import os
import stripe
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse
import pandas as pd
from io import BytesIO
from motor import executar_calculo_tb, rename_columns

app = FastAPI()

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
EMAIL_ADMIN = "abielgm@icloud.com"

@app.get("/", response_class=HTMLResponse)
async def interface():
    s_url = os.getenv("SUPABASE_URL", "")
    s_key = os.getenv("SUPABASE_KEY", "")

    return f"""
    <!DOCTYPE html>
    <html lang="pt-br">
    <head>
        <meta charset="UTF-8"><title>EstimaTB Pro - Login</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <script src="https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2"></script>
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
    </head>
    <body class="bg-slate-50 font-sans min-h-screen flex items-center justify-center p-4">
        
        <div class="max-w-md w-full">
            
            <!-- TELA DE LOGIN / CADASTRO -->
            <div id="login-section" class="bg-white p-8 rounded-3xl shadow-xl border border-gray-100">
                <div class="text-center mb-8">
                    <h1 class="text-4xl font-black text-green-700 italic">EstimaTB 🌿</h1>
                    <p class="text-gray-400 text-sm mt-1">Plataforma de Estimativa Agrometeorológica</p>
                </div>

                <div class="space-y-4">
                    <!-- Email -->
                    <div>
                        <label class="text-xs font-bold text-gray-400 uppercase ml-1">E-mail</label>
                        <input type="email" id="email" class="w-full border-2 border-gray-100 p-3 rounded-xl focus:border-green-500 outline-none transition-all">
                    </div>

                    <!-- Senha -->
                    <div class="relative">
                        <label class="text-xs font-bold text-gray-400 uppercase ml-1">Senha</label>
                        <input type="password" id="password" class="w-full border-2 border-gray-100 p-3 rounded-xl focus:border-green-500 outline-none transition-all">
                        <button onclick="togglePassword('password')" class="absolute right-4 top-8 text-gray-400 hover:text-green-600">
                            <i class="fas fa-eye" id="eye-password"></i>
                        </button>
                    </div>

                    <!-- Confirmar Senha (Apenas Cadastro) -->
                    <div id="confirm-box" class="relative hidden">
                        <label class="text-xs font-bold text-gray-400 uppercase ml-1">Confirmar Senha</label>
                        <input type="password" id="confirmPassword" class="w-full border-2 border-gray-100 p-3 rounded-xl focus:border-green-500 outline-none transition-all">
                        <button onclick="togglePassword('confirmPassword')" class="absolute right-4 top-8 text-gray-400 hover:text-green-600">
                            <i class="fas fa-eye" id="eye-confirm"></i>
                        </button>
                    </div>

                    <div class="flex flex-col gap-3 pt-4">
                        <button id="btnAuth" onclick="processarAuth()" class="w-full bg-green-600 text-white py-4 rounded-2xl font-black text-lg shadow-lg shadow-green-200 hover:bg-green-700 active:scale-95 transition-all">
                            ENTRAR
                        </button>
                        
                        <button id="btnSwitch" onclick="toggleMode()" class="text-green-700 font-bold text-sm hover:underline">
                            Não tem conta? Cadastre-se aqui
                        </button>
                    </div>
                </div>
            </div>

            <!-- TELA DO CALCULADOR (Escondida) -->
            <div id="main-section" class="hidden animate-in fade-in zoom-in duration-300">
                <div class="bg-white p-8 rounded-3xl shadow-xl border-b-8 border-green-600 mb-6">
                    <div class="flex justify-between items-center mb-6 border-b border-gray-50 pb-4">
                        <div class="flex flex-col">
                            <span class="text-[10px] font-black text-gray-300 uppercase">Pesquisador Logado</span>
                            <span id="user-display" class="font-bold text-gray-700"></span>
                        </div>
                        <button onclick="logout()" class="bg-red-50 text-red-500 text-xs font-black px-4 py-2 rounded-full hover:bg-red-500 hover:text-white transition-all">LOGOUT</button>
                    </div>
                    
                    <input type="file" id="arquivo" class="block w-full text-sm text-gray-500 file:mr-4 file:py-3 file:px-6 file:rounded-full file:border-0 file:text-sm file:font-black file:bg-green-50 file:text-green-700 hover:file:bg-green-100 mb-8 border-2 border-dashed border-gray-100 rounded-2xl p-4">
                    
                    <button id="btnCalc" onclick="calcular()" class="w-full bg-green-600 text-white py-4 rounded-2xl font-black text-xl shadow-xl shadow-green-100 hover:scale-[1.02] transition-all">ANALISAR DADOS</button>
                </div>

                <div id="resultado" class="hidden bg-white p-8 rounded-3xl shadow-2xl border-t-8 border-blue-500">
                    <h3 class="font-black text-gray-800 text-xl mb-6 text-center italic">Resultados de Campo</h3>
                    <div class="grid grid-cols-2 gap-4 mb-8">
                        <div class="bg-green-50 p-6 rounded-2xl text-center">
                            <span class="text-[10px] font-black text-green-800 uppercase block mb-1">Temperatura Basal</span>
                            <span id="res_tb" class="text-3xl font-black text-green-700">--</span>
                        </div>
                        <div class="bg-blue-50 p-6 rounded-2xl text-center">
                            <span class="text-[10px] font-black text-blue-800 uppercase block mb-1">Precisão (R²)</span>
                            <span id="res_r2" class="text-3xl font-black text-blue-700">--</span>
                        </div>
                    </div>
                    
                    <div id="paywall" class="p-6 bg-amber-50 rounded-2xl text-center border-2 border-amber-100 shadow-inner">
                        <p class="text-amber-900 font-bold mb-4 text-sm">Dados básicos carregados. Liberar STa acumulada e relatórios técnicos?</p>
                        <button onclick="pagar()" class="bg-amber-600 text-white px-8 py-3 rounded-full font-black text-lg hover:bg-amber-700 shadow-md">ATIVAR VERSÃO PRO</button>
                    </div>
                </div>
            </div>

        </div>

        <script>
            const _supabase = supabase.createClient("{s_url}", "{s_key}");
            const ADMIN_EMAIL = "{EMAIL_ADMIN}".toLowerCase();
            let mode = 'login';

            function togglePassword(id) {{
                const input = document.getElementById(id);
                const eye = document.getElementById(id === 'password' ? 'eye-password' : 'eye-confirm');
                if (input.type === 'password') {{
                    input.type = 'text';
                    eye.classList.replace('fa-eye', 'fa-eye-slash');
                }} else {{
                    input.type = 'password';
                    eye.classList.replace('fa-eye-slash', 'fa-eye');
                }}
            }}

            function toggleMode() {{
                mode = mode === 'login' ? 'signup' : 'login';
                document.getElementById('confirm-box').classList.toggle('hidden');
                document.getElementById('btnAuth').innerText = mode === 'login' ? 'ENTRAR' : 'CRIAR CONTA AGORA';
                document.getElementById('btnSwitch').innerText = mode === 'login' ? 'Não tem conta? Cadastre-se aqui' : 'Já tem conta? Faça Login';
            }}

            async function processarAuth() {{
                const email = document.getElementById('email').value;
                const password = document.getElementById('password').value;
                const confirm = document.getElementById('confirmPassword').value;
                const btn = document.getElementById('btnAuth');

                if(!email || !password) return alert("E-mail e Senha são obrigatórios.");
                
                if(mode === 'signup' && password !== confirm) {{
                    return alert("As senhas não coincidem!");
                }}

                btn.innerText = "PROCESSANDO...";
                btn.disabled = true;

                try {{
                    let res;
                    if(mode === 'login') {{
                        res = await _supabase.auth.signInWithPassword({{ email, password }});
                    }} else {{
                        res = await _supabase.auth.signUp({{ email, password }});
                    }}

                    if(res.error) throw res.error;
                    
                    if(mode === 'signup') alert("Conta criada com sucesso!");
                    window.location.reload();

                }} catch(err) {{
                    alert("Erro: " + err.message);
                }} finally {{
                    btn.innerText = mode === 'login' ? 'ENTRAR' : 'CRIAR CONTA AGORA';
                    btn.disabled = false;
                }}
            }}

            async function logout() {{
                await _supabase.auth.signOut();
                window.location.reload();
            }}

            async function checkUser() {{
                const {{ data: {{ user }} }} = await _supabase.auth.getUser();
                if (user) {{
                    document.getElementById('login-section').classList.add('hidden');
                    document.getElementById('main-section').classList.remove('hidden');
                    document.getElementById('user-display').innerText = user.email;
                    
                    if(user.email.toLowerCase() === ADMIN_EMAIL) {{
                        document.getElementById('paywall').innerHTML = '<div class="font-black text-green-700 italic border-2 border-green-200 p-2 rounded-xl bg-green-50">⭐ ACESSO TOTAL MASTER LIBERADO</div>';
                    }}
                }}
            }}
            checkUser();

            async function calcular() {{
                const file = document.getElementById('arquivo').files[0];
                if(!file) return alert("Selecione um arquivo .csv ou .xlsx!");
                const btn = document.getElementById('btnCalc');
                btn.innerText = "CÁLCULO EM CURSO...";
                btn.disabled = true;

                const fd = new FormData();
                fd.append('file', file);
                try {{
                    const r = await fetch('/analisar', {{ method: 'POST', body: fd }});
                    const d = await r.json();
                    document.getElementById('resultado').classList.remove('hidden');
                    document.getElementById('res_tb').innerText = d.tb_estimada + " ºC";
                    document.getElementById('res_r2').innerText = d.r2.toFixed(4);
                }} catch(e) {{
                    alert("Erro ao analisar arquivo.");
                }} finally {{
                    btn.innerText = "ANALISAR DADOS";
                    btn.disabled = false;
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

# --- MANTER ROTAS ABAIXO SEM ALTERAÇÃO ---
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
        line_items=[{'price_data': {'currency': 'brl', 'product_data': {'name': 'EstimaTB Pro - Relatórios Acadêmicos'}, 'unit_amount': 2990}, 'quantity': 1}],
        mode='payment',
        success_url='https://temperatura-basal.onrender.com', cancel_url='https://temperatura-basal.onrender.com',
    )
    return {"url": session.url}
