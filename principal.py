import os
import stripe
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse
import pandas as pd
from io import BytesIO
from motor import executar_calculo_tb, rename_columns

app = FastAPI()

# Configuração do Stripe (Backend)
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

# Seu e-mail de Administrador
EMAIL_ADMIN = "abielgm@icloud.com"

@app.get("/", response_class=HTMLResponse)
async def interface():
    # Buscamos as chaves que estão configuradas no Render para injetar no site
    s_url = os.getenv("SUPABASE_URL", "")
    s_key = os.getenv("SUPABASE_KEY", "")

    return f"""
    <!DOCTYPE html>
    <html lang="pt-br">
    <head>
        <meta charset="UTF-8"><title>EstimaTB Pro - Login</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <!-- Importando biblioteca oficial do Supabase -->
        <script src="https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2"></script>
    </head>
    <body class="bg-gray-100 font-sans">
        <div class="max-w-2xl mx-auto py-12 px-4">
            
            <!-- TELA DE LOGIN -->
            <div id="login-section" class="bg-white p-8 rounded-xl shadow-md text-center">
                <h1 class="text-4xl font-black text-green-700 mb-6 italic">EstimaTB 🌿</h1>
                <div class="space-y-4">
                    <input type="email" id="email" placeholder="E-mail Acadêmico" class="w-full border p-3 rounded-lg focus:ring-2 focus:ring-green-500 outline-none">
                    <input type="password" id="password" placeholder="Sua Senha" class="w-full border p-3 rounded-lg focus:ring-2 focus:ring-green-500 outline-none">
                    <div class="flex gap-2">
                        <button onclick="auth('login')" class="w-1/2 bg-green-600 text-white py-3 rounded-lg font-bold hover:bg-green-700 transition">Entrar</button>
                        <button onclick="auth('signup')" class="w-1/2 border-2 border-green-600 text-green-600 py-3 rounded-lg font-bold hover:bg-green-50 transition">Cadastrar</button>
                    </div>
                </div>
            </div>

            <!-- TELA DO CALCULADOR (Escondida) -->
            <div id="main-section" class="hidden">
                <div class="bg-white p-8 rounded-xl shadow-md mb-8 border-b-8 border-green-600">
                    <div class="flex justify-between items-center mb-6 border-b pb-4">
                        <p class="font-bold text-gray-700">Bem-vindo, <span id="user-display" class="text-green-600 font-black"></span></p>
                        <button onclick="logout()" class="text-red-500 text-sm font-bold border border-red-500 px-3 py-1 rounded-full hover:bg-red-50">Sair do App</button>
                    </div>
                    
                    <h2 class="text-sm font-black text-gray-500 uppercase mb-2">Upload de Arquivo Meteorológico</h2>
                    <input type="file" id="arquivo" class="block w-full border-2 border-dashed p-4 rounded-xl mb-6 bg-gray-50 hover:bg-white transition cursor-pointer">
                    
                    <button id="btn" onclick="calcular()" class="w-full bg-green-600 text-white py-4 rounded-xl font-black text-xl shadow-xl hover:scale-[1.02] transition-transform uppercase tracking-tighter">
                        Iniciar Estimativa Tb
                    </button>
                </div>

                <div id="resultado" class="hidden bg-white p-8 rounded-xl shadow-2xl border-t-8 border-blue-500 transition-all">
                    <h3 class="font-black text-gray-800 text-xl mb-6 text-center underline decoration-green-500">RELATÓRIO DE PROCESSAMENTO</h3>
                    <div class="grid grid-cols-1 sm:grid-cols-2 gap-6 mb-8">
                        <div class="bg-green-50 p-6 rounded-2xl text-center border-2 border-green-200">
                            <span class="text-xs font-black text-green-800 uppercase block mb-2 italic">Temperatura Basal Inferior</span>
                            <span id="res_tb" class="text-4xl font-black text-green-700 tracking-tight">--</span>
                        </div>
                        <div class="bg-blue-50 p-6 rounded-2xl text-center border-2 border-blue-200">
                            <span class="text-xs font-black text-blue-800 uppercase block mb-2 italic">Ajuste do Modelo (R²)</span>
                            <span id="res_r2" class="text-4xl font-black text-blue-700 tracking-tight">--</span>
                        </div>
                    </div>
                    
                    <div id="paywall" class="p-6 bg-yellow-50 rounded-2xl text-center border-2 border-yellow-200">
                        <p class="text-yellow-900 font-bold mb-4">A análise básica foi concluída. Deseja baixar os relatórios STa e gráficos profissionais para exportação?</p>
                        <button onclick="pagar()" class="bg-yellow-600 text-white px-8 py-3 rounded-full font-black text-lg hover:bg-yellow-700 shadow-lg transition">OBTER PACOTE COMPLETO PRO</button>
                    </div>
                </div>
            </div>
        </div>

        <script>
            // INJETANDO AS CHAVES DINAMICAMENTE
            const supabaseUrl = "{s_url}";
            const supabaseKey = "{s_key}";
            const ADMIN_EMAIL = "{EMAIL_ADMIN}".toLowerCase();
            
            // Inicializando o cliente Supabase
            const {{ createClient }} = supabase;
            const _supabase = createClient(supabaseUrl, supabaseKey);

            async function auth(type) {{
                const email = document.getElementById('email').value;
                const password = document.getElementById('password').value;
                if(!email || !password) return alert("Dados obrigatórios faltando.");

                let res;
                if(type === 'login') res = await _supabase.auth.signInWithPassword({{ email, password }});
                else res = await _supabase.auth.signUp({{ email, password }});
                
                if(res.error) alert("Erro: " + res.error.message);
                else window.location.reload();
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
                        document.getElementById('paywall').innerHTML = `
                            <div class="bg-green-100 p-4 border-l-4 border-green-600 text-green-800 font-black italic">
                                ⭐ CONTA MASTER: Todos os downloads de relatórios e funções científicas liberados.
                            </div>`;
                    }}
                }}
            }}
            checkUser();

            async function calcular() {{
                const btn = document.getElementById('btn');
                const file = document.getElementById('arquivo').files[0];
                if(!file) return alert("Escolha o arquivo .csv ou .xlsx!");

                btn.innerText = "SINCRO_PROCESSAMENTO EM CURSO...";
                btn.disabled = true;

                const fd = new FormData();
                fd.append('file', file);
                
                try {{
                    const response = await fetch('/analisar', {{ method: 'POST', body: fd }});
                    const data = await response.json();
                    
                    if(data.tb_estimada) {{
                        document.getElementById('resultado').classList.remove('hidden');
                        document.getElementById('res_tb').innerText = data.tb_estimada + " ºC";
                        document.getElementById('res_r2').innerText = data.r2.toFixed(4);
                        window.scrollTo({{ top: document.body.scrollHeight, behavior: 'smooth' }});
                    }} else {{
                        alert("Ocorreu um erro no processamento matemático.");
                    }}
                }} catch(e) {{
                    alert("Falha de conexão com o servidor de cálculo.");
                }} finally {{
                    btn.innerText = "Iniciar Estimativa Tb";
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

# --- ROTAS DE BACKEND ---

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
            "tb_estimada": round(resultado['melhor_resultado']['Temperatura (ºC)'], 2), 
            "r2": resultado['melhor_resultado']['R2']
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/checkout-stripe")
def criar_checkout():
    # Aqui criamos o produto "on-the-fly" para o checkout
    session = stripe.checkout.Session.create(
        payment_method_types=['card', 'pix'],
        line_items=[{
            'price_data': {
                'currency': 'brl', 
                'product_data': {'name': 'EstimaTB Pro - Licença de Uso Profissional'}, 
                'unit_amount': 2990, # R$ 29,90
            }, 
            'quantity': 1,
        }],
        mode='payment',
        success_url='https://temperatura-basal.onrender.com', 
        cancel_url='https://temperatura-basal.onrender.com',
    )
    return {"url": session.url}
