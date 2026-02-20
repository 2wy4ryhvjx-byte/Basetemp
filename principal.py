import os
import stripe
import pandas as pd
from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from fastapi.responses import HTMLResponse
from io import BytesIO, StringIO
from motor import executar_calculo_tb, rename_columns

app = FastAPI()

# Configuração de Logs no Render (verificaremos nos logs se as chaves existem)
stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "")
URL_SUPABASE = os.getenv("SUPABASE_URL", "URL_NAO_CONFIGURADA")
KEY_SUPABASE = os.getenv("SUPABASE_KEY", "KEY_NAO_CONFIGURADA")

# Log de segurança para conferir no Render Dashboard (aba Logs)
print(f"--- DIAGNOSTICO ---")
print(f"URL: {URL_SUPABASE[:15]}...")
print(f"KEY: {KEY_SUPABASE[:15]}...")

@app.get("/", response_class=HTMLResponse)
async def interface():
    # Carregamos o modelo de HTML (puro, sem f-string para evitar conflitos de chaves {})
    html_content = """
    <!DOCTYPE html>
    <html lang="pt-br">
    <head>
        <meta charset="UTF-8"><title>EstimaTB Pro</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <script src="https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2"></script>
        <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
    </head>
    <body class="bg-slate-100 font-sans min-h-screen">
        <!-- Loader -->
        <div id="loading" class="hidden fixed inset-0 bg-white/90 flex items-center justify-center z-50 flex-col">
            <div class="animate-spin rounded-full h-10 w-10 border-b-2 border-green-700 mb-2"></div>
            <p class="text-xs font-black text-green-800 animate-pulse uppercase italic">Processando Modelo Científico</p>
        </div>

        <div class="max-w-md mx-auto py-12 px-4" id="login-container">
            <!-- TELA DE LOGIN -->
            <div id="login-section" class="bg-white p-8 rounded-[2rem] shadow-2xl text-center border border-gray-100">
                <h1 class="text-4xl font-black text-green-700 mb-2 italic underline decoration-yellow-400">EstimaTB🌿</h1>
                <p class="text-[9px] font-black text-gray-300 uppercase tracking-widest mb-8 italic">Scientific Calculation Environment</p>
                
                <div class="space-y-4">
                    <input type="email" id="email" placeholder="E-mail Acadêmico" class="w-full border-2 p-4 rounded-2xl outline-none focus:border-green-600 transition-all">
                    <input type="password" id="password" placeholder="Senha" class="w-full border-2 p-4 rounded-2xl outline-none focus:border-green-600 transition-all">
                    
                    <div id="confirm-box" class="hidden">
                        <input type="password" id="confirmPassword" placeholder="Confirme a Senha" class="w-full border-2 p-4 rounded-2xl outline-none focus:border-green-600 transition-all">
                    </div>

                    <button id="btnAuth" onclick="handleAuth()" class="w-full bg-green-600 text-white py-4 rounded-2xl font-black text-lg shadow-lg hover:bg-green-700 active:scale-95 transition-all">ENTRAR</button>
                    <button id="btnSwitch" onclick="toggleMode()" class="w-full text-green-700 font-bold text-xs uppercase mt-2 hover:underline">Solicitar Novo Acesso</button>
                </div>
            </div>
        </div>

        <!-- DASHBOARD (Escondido) -->
        <div id="main-section" class="hidden max-w-6xl mx-auto p-4 md:p-8 animate-in fade-in duration-500">
            <div class="bg-white p-4 rounded-2xl shadow mb-6 flex justify-between items-center px-8 border">
                <p class="text-sm font-bold text-gray-500">User: <span id="user-display" class="text-green-700"></span></p>
                <button onclick="logout()" class="text-red-500 font-black text-xs hover:underline uppercase italic">Logout</button>
            </div>

            <div class="grid grid-cols-1 lg:grid-cols-12 gap-8">
                <div class="lg:col-span-4 bg-white p-8 rounded-[2rem] shadow-xl h-fit border">
                    <h3 class="font-black text-xs uppercase mb-6 border-b pb-2 text-gray-700">Painel de Configurações</h3>
                    <input type="text" id="nome_analise" placeholder="Identificação da Amostra" class="w-full border-2 p-3 rounded-xl mb-6 bg-slate-50 outline-none focus:border-green-500">
                    
                    <select id="src-mode" onchange="toggleInputs()" class="w-full border-2 p-3 rounded-xl mb-4 text-xs font-bold uppercase bg-white cursor-pointer">
                        <option value="file">Importar CSV / XLSX</option>
                        <option value="manual">Digitação Manual de Dados</option>
                    </select>

                    <div id="input-f"><input type="file" id="arquivo" class="block w-full text-xs border-2 border-dashed p-6 rounded-2xl bg-gray-50 mb-6"></div>
                    <div id="input-m" class="hidden"><textarea id="manual_data" placeholder="Data,Tmin,Tmax,NF" class="w-full border-2 p-3 rounded-xl h-40 font-mono text-xs bg-gray-50 mb-6"></textarea></div>

                    <div class="bg-slate-50 p-4 rounded-2xl mb-8">
                        <p class="text-[9px] font-black text-gray-400 mb-3 text-center uppercase tracking-tighter">Limites de Temperatura de Teste</p>
                        <div class="grid grid-cols-3 gap-2 text-center">
                            <div><label class="text-[8px] font-bold">Tb Mín</label><input type="number" id="tbmin" value="0.0" class="w-full border p-1 rounded font-bold text-center"></div>
                            <div><label class="text-[8px] font-bold">Tb Máx</label><input type="number" id="tbmax" value="20.0" class="w-full border p-1 rounded font-bold text-center"></div>
                            <div><label class="text-[8px] font-bold">Passo</label><input type="number" id="passo" value="0.5" step="0.1" class="w-full border p-1 rounded font-bold text-center"></div>
                        </div>
                    </div>
                    <button id="btnCalc" onclick="calcular()" class="w-full bg-green-600 text-white py-4 rounded-[1.5rem] font-black text-xl shadow-lg hover:scale-105 transition-all uppercase tracking-tighter italic">Analisar Modelo</button>
                </div>

                <div id="result-col" class="lg:col-span-8 hidden space-y-6">
                    <div class="bg-white p-8 rounded-[2.5rem] shadow-2xl border-t-8 border-slate-900">
                         <div class="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
                            <div class="bg-gray-50 p-6 rounded-2xl border border-gray-100 text-center shadow-inner"><span class="text-[9px] font-black text-gray-400 uppercase italic">Temp. Basal</span><p id="res-tb" class="text-3xl font-black text-slate-800">--</p></div>
                            <div class="bg-gray-50 p-6 rounded-2xl border border-gray-100 text-center shadow-inner"><span class="text-[9px] font-black text-gray-400 uppercase italic">Ajuste (R²)</span><p id="res-r2" class="text-3xl font-black text-slate-800">--</p></div>
                            <div class="bg-gray-50 p-6 rounded-2xl border border-gray-100 text-center shadow-inner"><span class="text-[9px] font-black text-gray-400 uppercase italic">QME</span><p id="res-qme" class="text-lg font-black text-slate-800">--</p></div>
                         </div>
                         <div class="grid grid-cols-1 md:grid-cols-2 gap-4 h-72">
                            <div id="plt-qme" class="w-full"></div>
                            <div id="plt-reg" class="w-full"></div>
                         </div>
                    </div>
                </div>
            </div>
        </div>

        <script>
            // VARIÁVEIS DE CONEXÃO
            const SURL = "VARIABLE_SURL";
            const SKEY = "VARIABLE_SKEY";

            if(SURL.includes("VARIABLE") || SURL === "") {
                alert("ERRO DE CONEXÃO: As chaves do servidor (Render) não foram entregues ao aplicativo. Por favor, faça um Manual Deploy -> Clear Cache no Render.");
            }

            const _supa = supabase.createClient(SURL, SKEY);
            let mode = 'login';

            function toggleMode() {
                mode = (mode === 'login') ? 'signup' : 'login';
                document.getElementById('confirm-box').classList.toggle('hidden', mode === 'login');
                document.getElementById('btnAuth').innerText = (mode === 'login') ? 'ENTRAR' : 'FINALIZAR CADASTRO';
            }

            function toggleInputs() {
                const isManual = document.getElementById('src-mode').value === 'manual';
                document.getElementById('input-f').classList.toggle('hidden', isManual);
                document.getElementById('input-m').classList.toggle('hidden', !isManual);
            }

            async function handleAuth() {
                const email = document.getElementById('email').value;
                const password = document.getElementById('password').value;
                if(!email || !password) return alert("E-mail e senha requeridos.");

                document.getElementById('btnAuth').innerText = "CONECTANDO...";
                try {
                    let r;
                    if(mode === 'login') r = await _supa.auth.signInWithPassword({email, password});
                    else r = await _supa.auth.signUp({email, password});

                    if(r.error) throw r.error;
                    location.reload();
                } catch(e) {
                    alert("Atenção: " + e.message);
                    document.getElementById('btnAuth').innerText = (mode === 'login') ? 'ENTRAR' : 'FINALIZAR CADASTRO';
                }
            }

            async function logout() { await _supa.auth.signOut(); location.reload(); }

            async function checkUser() {
                const {data:{user}} = await _supa.auth.getUser();
                if(user) {
                    document.getElementById('login-container').classList.add('hidden');
                    document.getElementById('main-section').classList.remove('hidden');
                    document.getElementById('user-display').innerText = user.email;
                }
            }
            checkUser();

            async function calcular() {
                document.getElementById('loading').classList.remove('hidden');
                const btn = document.getElementById('btnCalc');
                btn.disabled = true;

                const file = document.getElementById('arquivo').files[0];
                const manual = document.getElementById('manual_data').value;
                const mode = document.getElementById('src-mode').value;
                
                const fd = new FormData();
                if(mode==='file' && file) fd.append('file', file);
                else fd.append('manual_data', manual);
                fd.append('tmin', document.getElementById('tbmin').value);
                fd.append('tmax', document.getElementById('tbmax').value);
                fd.append('passo', document.getElementById('passo').value);

                try {
                    const res = await fetch('/analisar', {method: 'POST', body: fd});
                    const d = await res.json();
                    
                    document.getElementById('result-col').classList.remove('hidden');
                    document.getElementById('res-tb').innerText = d.best.t + "°C";
                    document.getElementById('res-r2').innerText = d.best.r2.toFixed(4);
                    document.getElementById('res-qme').innerText = d.best.qme.toFixed(6);

                    Plotly.newPlot('plt-qme', [{x: d.q_dat.t, y: d.q_dat.q, mode: 'lines+markers', line:{color:'black'}, marker:{color:'black'}}], {title:'Mínimo QME', margin:{t:30, b:40}});
                    Plotly.newPlot('plt-reg', [{x: d.reg.x, y: d.reg.y, mode: 'markers', marker:{color:'gray'}}, {x:d.reg.x, y:d.reg.p, mode:'lines', line:{color:'black', dash:'dot'}}], {title:'Regressão Intercepto', showlegend:false, margin:{t:30, b:40}});

                } catch(e) {
                    alert("Falha no processamento científico dos dados.");
                } finally {
                    document.getElementById('loading').classList.add('hidden');
                    btn.disabled = false;
                }
            }
        </script>
    </body>
    </html>
    """
    
    # Injetamos as variáveis de forma segura no HTML final usando .replace()
    final_html = html_content.replace("VARIABLE_SURL", URL_SUPABASE)
    final_html = final_html.replace("VARIABLE_SKEY", KEY_SUPABASE)
    
    return final_html

# --- ROTAS DE BACKEND ---

@app.post("/analisar")
async def analisar(
    file: UploadFile = None, 
    manual_data: str = Form(None),
    tmin: float = Form(0.0), tmax: float = Form(20.0), passo: float = Form(0.5)
):
    try:
        if file:
            content = await file.read()
            df = pd.read_csv(BytesIO(content), sep=None, engine='python') if file.filename.endswith('.csv') else pd.read_excel(BytesIO(content))
        elif manual_data:
            df = pd.read_csv(StringIO(manual_data), names=['Data', 'Tmin', 'Tmax', 'NF'], header=None)
        else:
            raise HTTPException(status_code=400, detail="Dados ausentes.")

        df = rename_columns(df)
        df['Data'] = pd.to_datetime(df['Data'], errors='coerce')
        res = executar_calculo_tb(df, tmin, tmax, passo)
        
        mdf = pd.DataFrame(res['tabela_meteorologica'])
        btb_s = str(round(res['melhor_resultado']['Temperatura (ºC)'], 2))
        idx_v = [i for i, v in enumerate(df['NF']) if not pd.isna(v)]

        return {
            "best": {"t": res['melhor_resultado']['Temperatura (ºC)'], "r2": res['melhor_resultado']['R2'], "qme": res['melhor_resultado']['QME']},
            "q_dat": {"t": [x['Temperatura (ºC)'] for x in res['tabela_erros']], "q": [x['QME'] for x in res['tabela_erros']]},
            "reg": {
                "x": [mdf.iloc[i][btb_s] for i in idx_v],
                "y": df['NF'].dropna().tolist(),
                "p": [mdf.iloc[i][btb_s] * res['melhor_resultado']['Coef_Angular'] + res['melhor_resultado']['Intercepto'] for i in idx_v]
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
