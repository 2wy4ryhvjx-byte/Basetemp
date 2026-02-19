import os
import stripe
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse
import pandas as pd
from io import BytesIO
from motor import executar_calculo_tb, rename_columns

app = FastAPI()

# Carregamento e Diagnóstico
s_url = os.getenv("SUPABASE_URL", "")
s_key = os.getenv("SUPABASE_KEY", "")

# Isso vai imprimir nos Logs do Render para você conferir:
print(f"DIAGNÓSTICO SUPABASE - URL ENCONTRADA: {s_url[:10]}...") 
print(f"DIAGNÓSTICO SUPABASE - KEY ENCONTRADA: {s_key[:10]}...")

stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "")
EMAIL_ADMIN = "abielgm@icloud.com"

@app.get("/", response_class=HTMLResponse)
async def interface():
    # Passamos as chaves para o HTML
    s_url = os.getenv("SUPABASE_URL", "")
    s_key = os.getenv("SUPABASE_KEY", "")

    return f"""
    <!DOCTYPE html>
    <html lang="pt-br">
    <head>
        <meta charset="UTF-8"><title>EstimaTB Pro</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <!-- Carregamento robusto da biblioteca do Supabase -->
        <script src="https://unpkg.com/@supabase/supabase-js@2.39.7/dist/umd/supabase.js"></script>
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
    </head>
    <body class="bg-slate-100 font-sans min-h-screen flex items-center justify-center p-4">
        
        <div class="max-w-md w-full">
            <div id="login-section" class="bg-white p-8 rounded-3xl shadow-2xl border border-gray-100">
                <div class="text-center mb-8">
                    <h1 class="text-4xl font-black text-green-700 italic tracking-tighter">EstimaTB 🌿</h1>
                    <p class="text-gray-400 text-[10px] font-bold uppercase mt-2">Ciência e Tecnologia de Precisão</p>
                </div>

                <div class="space-y-4">
                    <input type="email" id="email" placeholder="E-mail" class="w-full border-2 p-4 rounded-2xl focus:border-green-500 outline-none">
                    
                    <div class="relative">
                        <input type="password" id="password" placeholder="Senha" class="w-full border-2 p-4 rounded-2xl focus:border-green-500 outline-none">
                        <button onclick="togglePass('password')" class="absolute right-4 top-5 text-gray-300"><i class="fas fa-eye"></i></button>
                    </div>

                    <div id="confirm-box" class="relative hidden">
                        <input type="password" id="confirmPassword" placeholder="Confirmar Senha" class="w-full border-2 p-4 rounded-2xl focus:border-green-500 outline-none">
                    </div>

                    <button id="btnAuth" onclick="handleAuth()" class="w-full bg-green-600 text-white py-4 rounded-2xl font-black shadow-lg hover:bg-green-700 active:scale-95 transition-all">ENTRAR</button>
                    
                    <button id="btnSwitch" onclick="toggleMode()" class="w-full text-green-700 font-bold text-xs uppercase tracking-widest mt-2">Criar conta acadêmica</button>
                </div>
            </div>

            <!-- DASHBOARD (Escondido) -->
            <div id="main-section" class="hidden animate-pulse-slow">
                <div class="bg-white p-8 rounded-3xl shadow-xl border-b-8 border-green-600 mb-6 text-center">
                    <div class="flex justify-between items-center mb-4 text-xs font-bold text-gray-400">
                        <span id="user-display">--</span>
                        <button onclick="logout()" class="text-red-500 underline">SAIR</button>
                    </div>
                    <input type="file" id="arquivo" class="block w-full border-2 border-dashed p-6 rounded-2xl mb-6 cursor-pointer">
                    <button id="btnCalc" onclick="calcular()" class="w-full bg-green-600 text-white py-5 rounded-2xl font-black text-xl hover:scale-105 transition-all shadow-xl">ANALISAR DADOS</button>
                </div>

                <div id="resultado" class="hidden bg-white p-8 rounded-3xl shadow-2xl border-t-8 border-blue-500 scale-in-center">
                    <h3 class="font-black text-center mb-6">ESTIMATIVA TB CONCLUÍDA</h3>
                    <div class="grid grid-cols-2 gap-4">
                        <div class="bg-green-50 p-6 rounded-2xl text-center"><p class="text-[10px] font-bold text-green-700">TB</p><p id="res_tb" class="text-3xl font-black">--</p></div>
                        <div class="bg-blue-50 p-6 rounded-2xl text-center"><p class="text-[10px] font-bold text-blue-700">R²</p><p id="res_r2" class="text-3xl font-black">--</p></div>
                    </div>
                    <div id="paywall" class="mt-6 p-4 bg-amber-50 rounded-xl text-center border-2 border-amber-200">
                        <button onclick="pagar()" class="bg-amber-600 text-white px-6 py-2 rounded-full font-bold">BAIXAR RELATÓRIO PRO</button>
                    </div>
                </div>
            </div>
        </div>

        <script>
            // VERIFICAÇÃO INICIAL DAS CHAVES
            const SUPABASE_URL = "{s_url}";
            const SUPABASE_KEY = "{s_key}";
            const ADMIN_EMAIL = "{EMAIL_ADMIN}".toLowerCase();

            if(!SUPABASE_URL || !SUPABASE_KEY) {{
                alert("AVISO TÉCNICO: Chaves do Supabase não configuradas no Render!");
            }}

            const _supabase = window.supabase.createClient(SUPABASE_URL, SUPABASE_KEY);
            let mode = 'login';

            function toggleMode() {{
                mode = mode === 'login' ? 'signup' : 'login';
                document.getElementById('confirm-box').classList.toggle('hidden');
                document.getElementById('btnAuth').innerText = mode === 'login' ? 'ENTRAR' : 'FINALIZAR CADASTRO';
                document.getElementById('btnSwitch').innerText = mode === 'login' ? 'Criar conta acadêmica' : 'Já tenho conta';
            }}

            function togglePass(id) {{
                const x = document.getElementById(id);
                x.type = x.type === "password" ? "text" : "password";
            }}

            async function handleAuth() {{
                const email = document.getElementById('email').value;
                const password = document.getElementById('password').value;
                const confirm = document.getElementById('confirmPassword').value;

                if(!email || !password) return alert("E-mail e senha são necessários!");
                if(mode === 'signup' && password !== confirm) return alert("As senhas não coincidem!");

                document.getElementById('btnAuth').innerText = "CONECTANDO...";

                try {{
                    let result;
                    if(mode === 'login') {{
                        result = await _supabase.auth.signInWithPassword({{ email, password }});
                    }} else {{
                        result = await _supabase.auth.signUp({{ email, password }});
                    }}

                    if(result.error) throw result.error;
                    location.reload();

                }} catch (e) {{
                    alert("ERRO DE AUTENTICAÇÃO: " + e.message);
                }} finally {{
                    document.getElementById('btnAuth').innerText = mode === 'login' ? 'ENTRAR' : 'FINALIZAR CADASTRO';
                }}
            }}

            async function logout() {{
                await _supabase.auth.signOut();
                location.reload();
            }}

            async function checkSession() {{
                const {{ data: {{ user }} }} = await _supabase.auth.getUser();
                if(user) {{
                    document.getElementById('login-section').classList.add('hidden');
                    document.getElementById('main-section').classList.remove('hidden');
                    document.getElementById('user-display').innerText = user.email;
                    
                    if(user.email.toLowerCase() === ADMIN_EMAIL) {{
                        document.getElementById('paywall').innerHTML = '<div class="text-green-700 font-bold italic">⭐ MODO MASTER: DOWNLOADS LIBERADOS</div>';
                    }}
                }}
            }}
            checkSession();

            async function calcular() {{
                const file = document.getElementById('arquivo').files[0];
                if(!file) return alert("Escolha o arquivo!");
                const btn = document.getElementById('btnCalc');
                btn.innerText = "PROCESSANDO...";
                const fd = new FormData();
                fd.append('file', file);
                try {{
                    const r = await fetch('/analisar', {{ method: 'POST', body: fd }});
                    const d = await r.json();
                    document.getElementById('resultado').classList.remove('hidden');
                    document.getElementById('res_tb').innerText = d.tb_estimada + " ºC";
                    document.getElementById('res_r2').innerText = d.r2.toFixed(4);
                }} catch(e) {{
                    alert("Erro no cálculo técnico.");
                }} finally {{
                    btn.innerText = "ANALISAR DADOS";
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

# MANTENHA O RESTO DAS FUNÇÕES (@app.post("/analisar") etc.) COMO ESTÃO.
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
        line_items=[{'price_data': {'currency': 'brl', 'product_data': {'name': 'Relatório EstimaTB Pro'}, 'unit_amount': 2990}, 'quantity': 1}],
        mode='payment',
        success_url='https://temperatura-basal.onrender.com', cancel_url='https://temperatura-basal.onrender.com',
    )
    return {"url": session.url}
