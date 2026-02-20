import os
import stripe
import pandas as pd
from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from fastapi.responses import HTMLResponse
from io import BytesIO, StringIO
from motor import executar_calculo_tb, rename_columns

app = FastAPI()

# --- DADOS FIXOS PARA TESTE SEGURO ---
URL_S = "https://iuhtopexunirguxmjiey.supabase.co"
KEY_S = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Iml1aHRvcGV4dW5pcmd1eG1qaWV5Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzE1MjIzNTcsImV4cCI6MjA4NzA5ODM1N30.EjDui9gQ5AlRaNpoVQisGUoXmK3j74gwzq9QSguxq78"
stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "")
EMAIL_ADMIN = "abielgm@icloud.com"

@app.get("/", response_class=HTMLResponse)
async def interface():
    html_content = """
    <!DOCTYPE html>
    <html lang="pt-br">
    <head>
        <meta charset="UTF-8"><title>EstimaTB Pro - Laboratório</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <script src="https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2"></script>
        <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
    </head>
    <body class="bg-slate-50 font-sans min-h-screen text-slate-900">
        
        <div id="loading" class="hidden fixed inset-0 bg-white/80 flex items-center justify-center z-50 flex-col">
            <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-green-700 mb-4"></div>
            <p class="font-black text-green-800 italic animate-pulse">PROCESSANDO CÁLCULO CIENTÍFICO...</p>
        </div>

        <div class="max-w-6xl mx-auto p-4 md:p-10">
            <!-- TELA DE LOGIN -->
            <div id="login-section" class="max-w-md mx-auto bg-white p-10 rounded-[2.5rem] shadow-2xl mt-12 border border-slate-100 text-center">
                <h1 class="text-4xl font-black text-green-700 italic mb-2 tracking-tighter">EstimaTB🌿</h1>
                <p class="text-[10px] font-black text-slate-300 uppercase tracking-widest mb-8">Calculadora de Temperatura Basal</p>
                
                <div class="space-y-4">
                    <input type="email" id="email" placeholder="E-mail Acadêmico" class="w-full border-2 p-4 rounded-2xl outline-none focus:border-green-600 bg-slate-50">
                    <input type="password" id="password" placeholder="Senha" class="w-full border-2 p-4 rounded-2xl outline-none focus:border-green-600 bg-slate-50">
                    <div id="confirm-box" class="hidden">
                        <input type="password" id="confirmPassword" placeholder="Confirme sua senha" class="w-full border-2 p-4 rounded-2xl outline-none focus:border-green-600 bg-slate-50 mb-4">
                    </div>
                    <button onclick="handleAuth('login')" id="btnLogin" class="w-full bg-green-600 text-white py-4 rounded-2xl font-black shadow-lg hover:bg-green-700 transition-all uppercase italic">Entrar no Lab</button>
                    <button onclick="toggleMode()" id="btnSwitch" class="text-green-700 font-bold text-[10px] uppercase mt-2 tracking-widest hover:underline">Novo Cadastro Acadêmico</button>
                </div>
            </div>

            <!-- ÁREA PRINCIPAL -->
            <div id="main-section" class="hidden animate-in fade-in duration-500">
                <div class="flex flex-col md:flex-row justify-between items-center bg-white p-6 rounded-3xl shadow-sm border mb-6 gap-4">
                    <p class="font-bold text-slate-500 text-xs italic italic">User: <span id="user-display" class="text-green-700 font-black not-italic ml-1 font-mono uppercase tracking-tighter"></span></p>
                    <div id="admin-tag" class="hidden bg-green-100 text-green-800 text-[10px] font-black px-4 py-1 rounded-full border border-green-200">ADMIN MASTER</div>
                    <button onclick="logout()" class="text-slate-300 font-black text-[10px] hover:text-red-500 uppercase tracking-widest transition-all">Sair do Sistema</button>
                </div>

                <div class="grid grid-cols-1 lg:grid-cols-12 gap-8">
                    <!-- Configurações Side -->
                    <div class="lg:col-span-4 space-y-6">
                        <div class="bg-white p-8 rounded-[2rem] shadow-xl border">
                            <h3 class="font-black text-slate-800 text-xs uppercase mb-6 flex items-center underline decoration-green-500 italic">Parametrização da Amostra</h3>
                            <input type="text" id="nome_analise" placeholder="Identificação (Ex: Milho G1)" class="w-full border-2 p-4 rounded-2xl mb-6 bg-slate-50 text-sm outline-none focus:border-green-600">

                            <select id="mode-data" onchange="switchIn()" class="w-full border-2 p-3 rounded-2xl mb-4 text-xs font-black uppercase italic bg-white shadow-inner">
                                <option value="f">Importar Excel/CSV</option>
                                <option value="m">Digitação Direta</option>
                            </select>

                            <div id="div-f"><input type="file" id="arquivo" class="block w-full border-2 border-dashed p-6 rounded-2xl mb-6 bg-slate-50 cursor-pointer"></div>
                            <div id="div-m" class="hidden"><textarea id="manual_data" placeholder="Data, Tmin, Tmax, NF" class="w-full border-2 p-4 rounded-2xl mb-6 h-40 bg-slate-50 font-mono text-xs"></textarea></div>

                            <div class="bg-slate-50 p-6 rounded-[1.5rem] mb-6">
                                <div class="grid grid-cols-3 gap-2">
                                    <div class="text-center"><label class="text-[8px] font-bold">Mín</label><input type="number" id="tmin" value="0.0" class="w-full border text-center rounded p-1 font-bold"></div>
                                    <div class="text-center"><label class="text-[8px] font-bold">Máx</label><input type="number" id="tmax" value="20.0" class="w-full border text-center rounded p-1 font-bold"></div>
                                    <div class="text-center"><label class="text-[8px] font-bold text-green-700 underline">Passo</label><input type="number" id="passo" value="0.5" step="0.1" class="w-full border text-center rounded p-1 font-bold border-green-300"></div>
                                </div>
                            </div>
                            <button onclick="calcular()" id="btnCalc" class="w-full bg-green-600 text-white py-5 rounded-[1.5rem] font-black text-xl shadow-xl hover:scale-[1.03] transition-all uppercase tracking-tighter italic">Analisar Modelo</button>
                        </div>
                    </div>

                    <div id="result-view" class="lg:col-span-8 hidden space-y-6 animate-in slide-in-bottom duration-500">
                        <div class="bg-white p-8 rounded-[3rem] shadow-2xl border-t-[10px] border-slate-900">
                             <div class="grid grid-cols-3 gap-4 mb-8">
                                <div class="bg-slate-50 p-4 rounded-2xl border text-center"><span class="text-[9px] font-black text-slate-400">Tb</span><p id="r-tb" class="text-3xl font-black font-mono tracking-tighter">--</p></div>
                                <div class="bg-slate-50 p-4 rounded-2xl border text-center"><span class="text-[9px] font-black text-slate-400">R²</span><p id="r-r2" class="text-3xl font-black font-mono tracking-tighter">--</p></div>
                                <div class="bg-slate-50 p-4 rounded-2xl border text-center"><span class="text-[9px] font-black text-slate-400">QME</span><p id="r-qme" class="text-xs font-bold font-mono">--</p></div>
                             </div>
                             <div class="grid md:grid-cols-2 gap-4 h-80">
                                <div id="gr-qme" class="w-full border border-slate-100 rounded-3xl"></div>
                                <div id="gr-reg" class="w-full border border-slate-100 rounded-3xl"></div>
                             </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <script>
            // CONFIGURAÇÃO DIRETA DAS CHAVES PARA DIAGNÓSTICO
            const S_URL = "SET_URL";
            const S_KEY = "SET_KEY";

            const _supa = supabase.createClient(S_URL, S_KEY);
            const MASTER = "abielgm@icloud.com";
            let mode = 'login';

            function toggleMode() {
                mode = mode === 'login' ? 'signup' : 'login';
                document.getElementById('confirm-box').classList.toggle('hidden', mode === 'login');
                document.getElementById('btnSwitch').innerText = mode === 'login' ? 'Novo Cadastro Acadêmico' : 'Já possuo login';
                document.getElementById('btnLogin').innerText = mode === 'login' ? 'Entrar no Lab' : 'Finalizar Registro';
            }

            function switchIn() {
                const isM = document.getElementById('mode-data').value === 'm';
                document.getElementById('div-f').classList.toggle('hidden', isM);
                document.getElementById('div-m').classList.toggle('hidden', !isM);
            }

            async function handleAuth(t) {
                const email = document.getElementById('email').value;
                const password = document.getElementById('password').value;
                if(!email || !password) return alert("E-mail e Senha são campos obrigatórios.");
                
                document.getElementById('loading').classList.remove('hidden');
                
                try {
                    let r;
                    if(mode === 'login') r = await _supa.auth.signInWithPassword({email, password});
                    else r = await _supa.auth.signUp({email, password});
                    
                    if(r.error) throw r.error;
                    location.reload();
                } catch(e) {
                    alert("Aviso: " + e.message);
                } finally {
                    document.getElementById('loading').classList.add('hidden');
                }
            }

            async function checkS() {
                const {data:{user}} = await _supa.auth.getUser();
                if(user) {
                    document.getElementById('login-section').classList.add('hidden');
                    document.getElementById('main-section').classList.remove('hidden');
                    document.getElementById('user-display').innerText = user.email.toLowerCase();
                    if(user.email.toLowerCase() === MASTER.toLowerCase()) document.getElementById('admin-tag').classList.remove('hidden');
                }
            }
            checkS();
            function logout() { _supa.auth.signOut(); location.reload(); }

            async function calcular() {
                const f = document.getElementById('arquivo').files[0];
                const m = document.getElementById('manual_data').value;
                const mode_data = document.getElementById('mode-data').value;
                const b = document.getElementById('btnCalc');

                document.getElementById('loading').classList.remove('hidden');
                b.disabled = true;

                const fd = new FormData();
                if(mode_data === 'f') { if(!f) return alert("Arquivo não selecionado!"); fd.append('file', f); }
                else fd.append('manual_data', m);

                fd.append('tmin', document.getElementById('tmin').value);
                fd.append('tmax', document.getElementById('tmax').value);
                fd.append('passo', document.getElementById('passo').value);
                fd.append('analise', document.getElementById('nome_analise').value);

                try {
                    const res = await fetch('/analisar', {method: 'POST', body: fd});
                    const d = await res.json();
                    
                    document.getElementById('result-view').classList.remove('hidden');
                    document.getElementById('r-tb').innerText = d.best.t + "°C";
                    document.getElementById('r-r2').innerText = d.best.r2.toFixed(4);
                    document.getElementById('r-qme').innerText = d.best.qme.toFixed(8);

                    Plotly.newPlot('gr-qme', [{x:d.q.t, y:d.q.q, mode:'lines+markers', line:{color:'black'}}], {title:'Curva QME', margin:{t:40}});
                    Plotly.newPlot('gr-reg', [{x:d.reg.x, y:d.reg.y, mode:'markers', marker:{color:'gray'}}, {x:d.reg.x, y:d.reg.p, mode:'lines', line:{color:'black', dash:'dot'}}], {title:'Reta de Ajuste', showlegend:false, margin:{t:40}});

                } catch(e) {
                    alert("Falha científica: Verifique a organização dos dados.");
                } finally {
                    document.getElementById('loading').classList.add('hidden');
                    b.disabled = false;
                }}
        </script>
    </body>
    </html>
    """.replace("SET_URL", URL_S).replace("SET_KEY", KEY_S)
    return html_content

# --- BACKEND MANTÉM IGUAL ---
@app.post("/analisar")
async def analisar_dados(
    file: UploadFile = None, manual_data: str = Form(None), 
    analise: str = Form(""), tmin: float = Form(0.0), tmax: float = Form(20.0), passo: float = Form(0.5)
):
    try:
        if file:
            content = await file.read()
            df = pd.read_csv(BytesIO(content), sep=None, engine='python') if file.filename.endswith('.csv') else pd.read_excel(BytesIO(content))
        else:
            df = pd.read_csv(StringIO(manual_data), names=['Data', 'Tmin', 'Tmax', 'NF'], header=None)
        
        df = rename_columns(df)
        df['Data'] = pd.to_datetime(df['Data'], errors='coerce')
        res = executar_calculo_tb(df, tmin, tmax, passo)
        
        met = pd.DataFrame(res['tabela_meteorologica'])
        bst = str(round(res['melhor_resultado']['Temperatura (ºC)'], 2))
        idx = [i for i, v in enumerate(df['NF']) if not pd.isna(v)]
        
        return {
            "nome": analise,
            "best": {"t": res['melhor_resultado']['Temperatura (ºC)'], "r2": res['melhor_resultado']['R2'], "qme": res['melhor_resultado']['QME']},
            "q": {"t": [x['Temperatura (ºC)'] for x in res['tabela_erros']], "q": [x['QME'] for x in res['tabela_erros']]},
            "reg": {
                "x": [met.iloc[i][bst] for i in idx],
                "y": df['NF'].dropna().tolist(),
                "p": [met.iloc[i][bst] * res['melhor_resultado']['Coef_Angular'] + res['melhor_resultado']['Intercepto'] for i in idx]
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
