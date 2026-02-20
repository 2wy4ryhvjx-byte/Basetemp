import os
import stripe
import pandas as pd
import numpy as np
from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from fastapi.responses import HTMLResponse
from io import BytesIO, StringIO
# Importa do seu arquivo motor.py (certifique-se que motor.py está na mesma pasta no GitHub)
from motor import executar_calculo_tb, rename_columns

app = FastAPI()

# =========================================================================
# CONFIGURAÇÕES TÉCNICAS
# =========================================================================
S_URL = "https://iuhtopexunirguxmjiey.supabase.co"
S_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Iml1aHRvcGV4dW5pcmd1eG1qaWV5Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzE1MjIzNTcsImV4cCI6MjA4NzA5ODM1N30.EjDui9gQ5AlRaNpoVQisGUoXmK3j74gwzq9QSguxq78"
stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "")
EMAIL_ADMIN = "abielgm@icloud.com"

@app.get("/", response_class=HTMLResponse)
async def interface():
    # Carregando HTML puro via replace para evitar erros de chaves { } do Python
    html_raw = """
    <!DOCTYPE html>
    <html lang="pt-br">
    <head>
        <meta charset="UTF-8"><title>EstimaTB Pro 🌿</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <script src="https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2"></script>
        <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
        <style>
            .grid-in { width: 100%; border: 1px solid #edf2f7; padding: 4px; font-size: 11px; text-align: center; outline: none; }
            .grid-in:focus { background: #f0fdf4; border-color: #16a34a; }
            .head-in { background: #f8fafc; font-size: 9px; font-weight: 900; color: #64748b; padding: 8px; border: 1px solid #e2e8f0; }
        </style>
    </head>
    <body class="bg-slate-50 font-sans min-h-screen">
        <div id="loading" class="hidden fixed inset-0 bg-white/95 flex items-center justify-center z-50 flex-col">
            <div class="animate-spin rounded-full h-10 w-10 border-4 border-green-700 border-t-transparent mb-4"></div>
            <p class="font-black text-green-800 animate-pulse italic">PROCESSANDO MODELO CIENTÍFICO...</p>
        </div>

        <div class="max-w-6xl mx-auto p-4 md:p-10">
            <!-- LOGIN -->
            <div id="login-section" class="max-w-md mx-auto bg-white p-10 rounded-[2.5rem] shadow-2xl mt-10 text-center border">
                <h1 class="text-4xl font-black text-green-700 italic mb-2 tracking-tighter uppercase underline decoration-yellow-400">EstimaTB🌿</h1>
                <p class="text-[9px] font-bold text-slate-300 uppercase tracking-widest mb-8">SECURE ENVIRONMENT</p>
                <div class="space-y-3">
                    <input type="email" id="email" placeholder="E-mail" class="w-full border p-3 rounded-2xl bg-slate-50 outline-none focus:border-green-600 shadow-inner">
                    <input type="password" id="password" placeholder="Senha" class="w-full border p-3 rounded-2xl bg-slate-50 outline-none focus:border-green-600 shadow-inner">
                    <button onclick="handleAuth('login')" id="btnLogin" class="w-full bg-green-600 text-white py-3 rounded-2xl font-black shadow-lg">ENTRAR</button>
                    <button onclick="toggleMode()" id="btnSwitch" class="text-green-600 font-bold text-[9px] uppercase mt-2 tracking-widest">Cadastro Acadêmico</button>
                </div>
            </div>

            <!-- WORKSTATION -->
            <div id="main-section" class="hidden">
                <div class="flex justify-between items-center bg-white p-5 rounded-[1.5rem] shadow-sm border mb-6 px-10">
                    <p class="text-slate-400 font-bold text-xs italic">Researcher: <span id="user-display" class="text-green-700 font-black not-italic"></span></p>
                    <button onclick="logout()" class="text-red-500 font-black text-[10px] uppercase underline transition-all">Sair do Lab</button>
                </div>

                <div class="grid grid-cols-1 lg:grid-cols-12 gap-8">
                    <div class="lg:col-span-5 bg-white p-8 rounded-[2.5rem] shadow-xl border">
                        <input type="text" id="analise_nome" placeholder="Nome do Experimento (Ex: Milho Anita)" class="w-full border-2 p-3 rounded-xl mb-6 bg-slate-50 text-sm font-bold">
                        
                        <div class="flex bg-slate-100 p-1 rounded-2xl mb-6 shadow-inner">
                            <button onclick="setMode('f')" id="btn-f" class="flex-1 py-3 text-[10px] font-black rounded-xl bg-white shadow text-green-700 uppercase">Arquivo Anexo</button>
                            <button onclick="setMode('m')" id="btn-m" class="flex-1 py-3 text-[10px] font-black rounded-xl text-slate-400 uppercase tracking-tighter">Entrada Manual</button>
                        </div>

                        <div id="ui-f" class="mb-6 text-center border-2 border-dashed p-6 rounded-2xl">
                            <input type="file" id="arquivo" class="text-[10px]">
                        </div>

                        <div id="ui-m" class="hidden mb-6 text-center">
                            <p class="text-[9px] font-bold text-slate-400 uppercase mb-2">Cole dados do Excel abaixo (Data | Tmin | Tmax | Var)</p>
                            <table class="w-full border" id="grid-tbl">
                                <thead><tr><th class="head-in">Data</th><th class="head-in">Min</th><th class="head-in">Max</th><th class="head-in">Var</th></tr></thead>
                                <tbody id="grid-body"></tbody>
                            </table>
                            <button onclick="addRow(5)" class="text-[9px] mt-2 text-green-600 font-bold underline uppercase">+ Linhas</button>
                        </div>

                        <div class="bg-slate-50 p-6 rounded-2xl border text-center grid grid-cols-3 gap-2 mb-8">
                            <div class="flex flex-col"><label class="text-[8px] font-bold">T-MIN</label><input type="number" id="tmin" value="0.0" class="w-full border p-1 rounded-lg text-center font-bold"></div>
                            <div class="flex flex-col"><label class="text-[8px] font-bold">T-MÁX</label><input type="number" id="tmax" value="20.0" class="w-full border p-1 rounded-lg text-center font-bold"></div>
                            <div class="flex flex-col"><label class="text-[8px] font-bold">PASSO</label><input type="number" id="passo" value="0.5" step="0.1" class="w-full border p-1 rounded-lg text-center font-bold text-green-600 border-green-200"></div>
                        </div>

                        <button onclick="calcular()" class="w-full bg-green-600 text-white py-5 rounded-[1.5rem] font-black text-xl shadow-xl hover:scale-[1.03] transition-all uppercase italic">Executar Análise</button>
                    </div>

                    <div id="results-view" class="lg:col-span-7 hidden animate-in slide-in-bottom">
                        <div class="bg-white p-8 rounded-[2.5rem] shadow-2xl border-t-[10px] border-slate-900 mb-8">
                            <h2 class="text-xl font-black italic border-b pb-4 mb-6">Métricas Modelagem</h2>
                             <div class="grid grid-cols-3 gap-4 mb-6">
                                <div class="bg-slate-50 p-4 rounded-xl text-center border shadow-inner">
                                    <span class="text-[9px] font-black text-slate-400">Tb Sugerida</span>
                                    <p id="v-tb" class="text-2xl font-black">--</p>
                                </div>
                                <div class="bg-slate-50 p-4 rounded-xl text-center border border-green-100 shadow-inner">
                                    <span class="text-[9px] font-black text-green-600">Ajuste R²</span>
                                    <p id="v-r2" class="text-2xl font-black text-green-700">--</p>
                                </div>
                                <div class="bg-slate-50 p-4 rounded-xl text-center border shadow-inner">
                                    <span class="text-[9px] font-black text-slate-400 italic">Mínimo QME</span>
                                    <p id="v-qme" class="text-[10px] font-bold">--</p>
                                </div>
                             </div>
                             <div class="grid grid-cols-1 md:grid-cols-2 gap-4 h-[350px]">
                                <div id="gr-qme" class="border rounded-2xl h-full w-full"></div>
                                <div id="gr-reg" class="border rounded-2xl h-full w-full"></div>
                             </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <script>
            const _supa = supabase.createClient("CONFIG_URL", "CONFIG_KEY");
            const MASTER = "abielgm@icloud.com";
            let mode = 'f'; let authMode = 'login';

            function addRow(n=1) {
                const tbody = document.getElementById('grid-body');
                for(let i=0;i<n;i++) {
                    const tr = document.createElement('tr');
                    tr.innerHTML = '<td><input type="text" class="grid-in dat-c"></td><td><input type="text" class="grid-in tmi-c"></td><td><input type="text" class="grid-in tma-c"></td><td><input type="text" class="grid-in var-c"></td>';
                    tbody.appendChild(tr);
                }
            }
            addRow(10);

            // FUNÇÃO COLAR EXCEL
            document.addEventListener('paste', function(e) {
                if(e.target.classList.contains('grid-in')) {
                    e.preventDefault();
                    const text = e.clipboardData.getData('text');
                    const rows = text.split(/\\r?\\n/);
                    let startTr = e.target.closest('tr');
                    rows.forEach(rText => {
                        if(rText.trim()==='') return;
                        const cols = rText.split('\\t');
                        const ins = startTr.querySelectorAll('input');
                        cols.forEach((v, idx) => { if(ins[idx]) ins[idx].value = v.trim(); });
                        startTr = startTr.nextElementSibling;
                        if(!startTr) { addRow(1); startTr = document.getElementById('grid-body').lastElementChild; }
                    });
                }
            });

            function setMode(m) {
                mode = m;
                document.getElementById('btn-f').classList.toggle('bg-white', m=='f');
                document.getElementById('btn-m').classList.toggle('bg-white', m=='m');
                document.getElementById('ui-f').classList.toggle('hidden', m=='m');
                document.getElementById('ui-m').classList.toggle('hidden', m=='f');
            }

            function toggleMode() {
                authMode = (authMode === 'login') ? 'signup' : 'login';
                document.getElementById('confirm-box').classList.toggle('hidden', authMode==='login');
                document.getElementById('btnLogin').innerText = (authMode==='login') ? 'ENTRAR' : 'FINALIZAR REGISTRO';
            }

            async function handleAuth(t) {
                const email = document.getElementById('email').value, p = document.getElementById('password').value;
                document.getElementById('loading').classList.remove('hidden');
                let r = (t==='login') ? await _supa.auth.signInWithPassword({email, password:p}) : await _supa.auth.signUp({email, password:p});
                if(r.error) { alert("Autenticação: " + r.error.message); document.getElementById('loading').classList.add('hidden'); }
                else location.reload();
            }

            async function checkS() {
                const {data:{user}} = await _supa.auth.getUser();
                if(user) {
                    document.getElementById('login-section').classList.add('hidden');
                    document.getElementById('main-section').classList.remove('hidden');
                    document.getElementById('user-display').innerText = user.email.toLowerCase();
                }
            }
            checkS();
            function logout() { _supa.auth.signOut(); window.location.replace('/'); }

            async function calcular() {
                document.getElementById('loading').classList.remove('hidden');
                const fd = new FormData();
                fd.append('analise', document.getElementById('analise_nome').value);
                fd.append('tmin', document.getElementById('tmin').value);
                fd.append('tmax', document.getElementById('tmax').value);
                fd.append('passo', document.getElementById('passo').value);

                if(mode === 'f') {
                    const f = document.getElementById('arquivo').files[0];
                    if(!f) { alert("Anexe o arquivo!"); document.getElementById('loading').classList.add('hidden'); return; }
                    fd.append('file', f);
                } else {
                    let rArr = [];
                    document.querySelectorAll('#grid-body tr').forEach(tr => {
                        const vals = Array.from(tr.querySelectorAll('input')).map(i => i.value.trim());
                        if(vals[0] && vals[1]) rArr.push(vals.join(','));
                    });
                    if(rArr.length < 3) { alert("Tabela insuficiente!"); document.getElementById('loading').classList.add('hidden'); return; }
                    fd.append('manual_data', rArr.join('\\n'));
                }

                try {
                    const res = await fetch('/analisar', {method:'POST', body:fd});
                    const d = await res.json();
                    if(d.detail) throw new Error(d.detail);
                    document.getElementById('results-view').classList.remove('hidden');
                    document.getElementById('v-tb').innerText = d.best.t + "°C";
                    document.getElementById('v-r2').innerText = d.best.r2.toFixed(4);
                    document.getElementById('v-qme').innerText = d.best.qme.toFixed(8);
                    Plotly.newPlot('gr-qme', [{x:d.q.t, y:d.q.q, mode:'lines+markers', line:{color:'black'}, marker:{color:'black'}}], {title:'Min QME', margin:{t:40}});
                    Plotly.newPlot('gr-reg', [{x:d.reg.x, y:d.reg.y, mode:'markers', marker:{color:'gray'}}, {x:d.reg.x, y:d.reg.p, mode:'lines', line:{color:'black', dash:'dot'}}], {title:'Ajuste', margin:{t:40}});
                } catch(e) {
                    alert("ERRO: O processamento falhou. Certifique-se de que a variável é cumulativa.");
                } finally { document.getElementById('loading').classList.add('hidden'); }
            }
        </script>
    </body>
    </html>
    """.replace("CONFIG_URL", S_URL).replace("CONFIG_KEY", S_KEY)
    return html_raw

# --- BACKEND ---
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
        # Limpeza para ignorar apenas se os 3 primeiros forem NaN, mas permitir NF=NaN
        df = df.dropna(subset=['Data', 'Tmin', 'Tmax'])
        df['NF'] = pd.to_numeric(df['NF'].astype(str).str.replace(',', '.').replace('nan', np.nan), errors='coerce')
        
        # Chamando o motor técnico
        res = executar_calculo_tb(df, tmin, tmax, passo)
        mdf = pd.DataFrame(res['tabela_meteorologica'])
        best_f = float(res['melhor_resultado']['Temperatura (ºC)'])
        c_floats = [float(c) for c in mdf.columns if c not in ['Dia', 'Mês', 'Ano', 'Tmin', 'Tmax', 'Tmed']]
        target_c = str(c_floats[np.abs(np.array(c_floats) - best_f).argmin()])
        idx_vals = [i for i, v in enumerate(df['NF']) if not pd.isna(v)]
        
        return {
            "best": {"t": res['melhor_resultado']['Temperatura (ºC)'], "r2": res['melhor_resultado']['R2'], "qme": res['melhor_resultado']['QME']},
            "q": {"t": [x['Temperatura (ºC)'] for x in res['tabela_erros']], "q": [x['QME'] for x in res['tabela_erros']]},
            "reg": {
                "x": [float(mdf.iloc[i][target_c]) for i in idx_vals],
                "y": df['NF'].dropna().astype(float).tolist(),
                "p": [float(mdf.iloc[i][target_c] * res['melhor_resultado']['Coef_Angular'] + res['melhor_resultado']['Intercepto']) for i in idx_vals]
            }
        }
    except Exception as e:
        return {"detail": str(e)}
