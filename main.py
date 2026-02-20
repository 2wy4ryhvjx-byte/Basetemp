import os
import stripe
import pandas as pd
import numpy as np
import unicodedata
from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from fastapi.responses import HTMLResponse
from io import BytesIO, StringIO
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_squared_error

app = FastAPI()

# =========================================================================
# CONFIGURAÇÕES DE ACESSO (PROTEGIDO)
# =========================================================================
S_URL = "https://iuhtopexunirguxmjiey.supabase.co"
S_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Iml1aHRvcGV4dW5pcmd1eG1qaWV5Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzE1MjIzNTcsImV4cCI6MjA4NzA5ODM1N30.EjDui9gQ5AlRaNpoVQisGUoXmK3j74gwzq9QSguxq78"
stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "")
EMAIL_ADMIN = "abielgm@icloud.com"

# =========================================================================
# FUNÇÕES CIENTÍFICAS INTEGRADAS
# =========================================================================
def normalize_txt(text):
    if not isinstance(text, str): return text
    return "".join(c for c in unicodedata.normalize('NFKD', text) if not unicodedata.combining(c)).lower().replace(" ", "").replace("_", "")

def preparar_dataframe(df):
    COLUMN_MAP = {'data': 'Data', 'tmin': 'Tmin', 'tmín': 'Tmin', 'tmax': 'Tmax', 'tmáx': 'Tmax', 'nf': 'NF', 'variavel': 'NF'}
    df.rename(columns=lambda col: COLUMN_MAP.get(normalize_txt(col), col), inplace=True)
    
    # Tratamento de datas brasileiras e tipos numéricos
    df['Data'] = pd.to_datetime(df['Data'], dayfirst=True, errors='coerce')
    for c in ['Tmin', 'Tmax', 'NF']:
        df[c] = pd.to_numeric(df[c].astype(str).str.replace(',', '.').replace('nan', np.nan), errors='coerce')
    
    return df.dropna(subset=['Data', 'Tmin', 'Tmax']).sort_values('Data')

# =========================================================================
# INTERFACE WEB (HTML/JS)
# =========================================================================
@app.get("/", response_class=HTMLResponse)
async def interface():
    html_content = """
    <!DOCTYPE html>
    <html lang="pt-br">
    <head>
        <meta charset="UTF-8"><title>EstimaTB Pro 🌿</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <script src="https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2"></script>
        <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
        <style>
            .spreadsheet-in { width: 100%; border: 1px solid #e2e8f0; padding: 6px; font-size: 11px; text-align: center; outline: none; font-family: monospace; }
            .spreadsheet-in:focus { background-color: #f0fdf4; border-color: #16a34a; }
            .header-lab { background: #f8fafc; font-size: 10px; font-weight: 900; color: #64748b; padding: 10px; border: 1px solid #e2e8f0; text-transform: uppercase; }
        </style>
    </head>
    <body class="bg-slate-50 font-sans min-h-screen">
        
        <div id="loader" class="hidden fixed inset-0 bg-white/95 flex items-center justify-center z-50 flex-col">
            <div class="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-green-700 mb-4"></div>
            <p class="font-black text-green-900 animate-pulse italic">PROCESSANDO MODELO CIENTÍFICO...</p>
        </div>

        <div class="max-w-6xl mx-auto p-4 md:p-10">
            <!-- TELA DE LOGIN -->
            <div id="login-section" class="max-w-md mx-auto bg-white p-10 rounded-[2.5rem] shadow-2xl mt-12 text-center border">
                <h1 class="text-4xl font-black text-green-700 italic mb-1 italic">EstimaTB🌿</h1>
                <p class="text-[9px] font-bold text-slate-300 uppercase tracking-widest mb-8 italic">Scientific Lab Workspace</p>
                <div class="space-y-4">
                    <input type="email" id="email" placeholder="E-mail Acadêmico" class="w-full border-2 p-4 rounded-2xl outline-none focus:border-green-600 bg-slate-50">
                    <input type="password" id="password" placeholder="Senha" class="w-full border-2 p-4 rounded-2xl outline-none focus:border-green-600 bg-slate-50">
                    <button onclick="auth('login')" id="btnLogin" class="w-full bg-green-600 text-white py-4 rounded-2xl font-black shadow-lg">ENTRAR</button>
                    <button onclick="toggleMode()" id="btnSwitch" class="text-green-600 font-bold text-[10px] uppercase mt-2">Criar Cadastro</button>
                </div>
            </div>

            <!-- DASHBOARD -->
            <div id="main-section" class="hidden">
                <div class="flex justify-between items-center bg-white p-6 rounded-[2rem] shadow-sm border mb-8 px-10">
                    <p class="text-slate-400 font-bold text-xs">Researcher: <span id="user-display" class="text-green-700 font-black not-italic uppercase tracking-tight"></span></p>
                    <button onclick="logout()" class="text-red-500 font-black text-[10px] uppercase underline transition-all italic">Encerrar Lab</button>
                </div>

                <div class="grid grid-cols-1 lg:grid-cols-12 gap-8">
                    <!-- Config Side -->
                    <div class="lg:col-span-5 space-y-6">
                        <div class="bg-white p-8 rounded-[2.5rem] shadow-xl border">
                            <h3 class="font-black text-slate-800 text-[11px] uppercase mb-6 flex items-center border-b pb-4 italic"><i class="fas fa-microscope mr-2 text-green-600"></i>Parâmetros do Experimento</h3>
                            
                            <input type="text" id="analise_nome" placeholder="Identificação da Amostra" class="w-full border-2 p-4 rounded-2xl mb-6 bg-slate-50 text-sm focus:border-green-600 outline-none">

                            <div class="flex bg-slate-100 p-1 rounded-2xl mb-6">
                                <button onclick="setTab('f')" id="tab-f" class="flex-1 py-3 text-[10px] font-black rounded-xl bg-white shadow-sm text-green-700 uppercase">Arquivo Anexo</button>
                                <button onclick="setTab('m')" id="tab-m" class="flex-1 py-3 text-[10px] font-black rounded-xl text-slate-400 uppercase italic">Colar Excel</button>
                            </div>

                            <div id="ui-f"><input type="file" id="arquivo" class="block w-full border-2 border-dashed p-10 rounded-2xl bg-slate-50 cursor-pointer text-xs"></div>

                            <div id="ui-m" class="hidden">
                                <div class="bg-white rounded-xl border overflow-hidden shadow-inner mb-2 max-h-80 overflow-y-auto">
                                    <table class="w-full border-collapse" id="spreadsheet">
                                        <thead>
                                            <tr>
                                                <th class="header-lab">Data</th>
                                                <th class="header-lab">Min</th>
                                                <th class="header-lab">Max</th>
                                                <th class="header-lab">Variável</th>
                                            </tr>
                                        </thead>
                                        <tbody id="manual-body"></tbody>
                                    </table>
                                </div>
                                <button onclick="addRow(10)" class="text-[9px] font-black text-green-600 uppercase mb-4 tracking-tighter underline">+ Linhas</button>
                            </div>

                            <div class="bg-slate-50 p-6 rounded-3xl border text-center shadow-inner mt-4">
                                <div class="grid grid-cols-3 gap-2">
                                    <div><label class="text-[8px] font-bold block">Min</label><input type="number" id="tmin" value="0.0" class="w-full border p-2 rounded-xl text-center font-bold"></div>
                                    <div><label class="text-[8px] font-bold block">Max</label><input type="number" id="tmax" value="20.0" class="w-full border p-2 rounded-xl text-center font-bold"></div>
                                    <div><label class="text-[8px] font-bold block text-green-700">Passo</label><input type="number" id="passo" value="0.5" step="0.1" class="w-full border p-2 rounded-xl text-center font-bold border-green-200"></div>
                                </div>
                            </div>

                            <button onclick="processar()" id="btnCalc" class="mt-8 w-full bg-green-600 text-white py-5 rounded-[1.8rem] font-black text-xl shadow-xl hover:scale-105 transition-all">ANALISAR CAMPO</button>
                        </div>
                    </div>

                    <!-- Saída Gráfica -->
                    <div id="results-col" class="lg:col-span-7 hidden animate-in slide-in-from-right">
                        <div class="bg-white p-10 rounded-[3.5rem] shadow-2xl border-t-[14px] border-slate-900 mb-8 h-fit sticky top-10">
                            <h2 class="text-xl font-black italic border-b pb-4 mb-10 text-slate-800" id="final-name">🔬 Resultados Encontrados</h2>
                             <div class="grid grid-cols-3 gap-4 mb-10 text-center">
                                <div class="bg-slate-50 p-6 rounded-3xl border shadow-inner"><p class="text-[9px] font-black text-slate-400">Tb (°C)</p><p id="v-tb" class="text-4xl font-black font-mono tracking-tighter">--</p></div>
                                <div class="bg-slate-50 p-6 rounded-3xl border border-green-50 shadow-inner"><p class="text-[9px] font-black text-green-600">Ajuste R²</p><p id="v-r2" class="text-4xl font-black font-mono text-green-700">--</p></div>
                                <div class="bg-slate-50 p-6 rounded-3xl border shadow-inner"><p class="text-[9px] font-black text-slate-400 italic">Erro QME</p><p id="v-qme" class="text-[12px] font-bold font-mono">--</p></div>
                             </div>
                             
                             <div class="space-y-6">
                                <div id="gr-qme" class="h-64 border-2 rounded-3xl bg-white shadow-inner overflow-hidden"></div>
                                <div id="gr-reg" class="h-64 border-2 rounded-3xl bg-white shadow-inner overflow-hidden"></div>
                             </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <script>
            const SURL = "CONFIG_SURL"; const SKEY = "CONFIG_SKEY"; const MASTER = "abielgm@icloud.com";
            const _supabase = supabase.createClient(SURL, SKEY);
            let activeTab = 'f';

            function initGrid() { document.getElementById('manual-body').innerHTML = ''; addRow(15); }
            function addRow(n) {
                const b = document.getElementById('manual-body');
                for(let i=0;i<n;i++) {
                    const r = document.createElement('tr');
                    r.innerHTML = '<td><input type="text" class="spreadsheet-in dat"></td><td><input type="text" class="spreadsheet-in tmi"></td><td><input type="text" class="spreadsheet-in tma"></td><td><input type="text" class="spreadsheet-in nfc"></td>';
                    b.appendChild(r);
                }
            }
            initGrid();

            // FUNÇÃO CTRL+V EXCEL
            document.addEventListener('paste', function(e) {
                if(e.target.classList.contains('spreadsheet-in')) {
                    e.preventDefault();
                    const clip = e.clipboardData.getData('text');
                    const rows = clip.split(/\\r?\\n/);
                    let tr = e.target.closest('tr');
                    rows.forEach(rStr => {
                        if(rStr.trim()==='') return;
                        const dataCells = rStr.split('\\t');
                        const inputs = tr.querySelectorAll('input');
                        dataCells.forEach((val, i) => { if(inputs[i]) inputs[i].value = val.trim(); });
                        tr = tr.nextElementSibling;
                        if(!tr) { addRow(1); tr = document.getElementById('manual-body').lastElementChild; }
                    });
                }
            });

            async function auth(t) {
                const email = document.getElementById('email').value, password = document.getElementById('password').value;
                document.getElementById('loader').classList.remove('hidden');
                let res = (t === 'login') ? await _supabase.auth.signInWithPassword({email, password}) : await _supabase.auth.signUp({email, password});
                if(res.error) { alert("Autenticação: " + res.error.message); document.getElementById('loader').classList.add('hidden'); }
                else location.reload();
            }

            async function checkUser() {
                const {data:{user}} = await _supabase.auth.getUser();
                if(user) {
                    document.getElementById('login-section').classList.add('hidden');
                    document.getElementById('main-section').classList.remove('hidden');
                    document.getElementById('user-display').innerText = user.email.toLowerCase();
                }
            }
            checkUser();
            async function logout() { await _supabase.auth.signOut(); localStorage.clear(); window.location.replace('/'); }

            function setTab(t) {
                activeTab = t;
                document.getElementById('tab-f').classList.toggle('bg-white', t=='f');
                document.getElementById('tab-m').classList.toggle('bg-white', t=='m');
                document.getElementById('ui-f').classList.toggle('hidden', t=='m');
                document.getElementById('ui-m').classList.toggle('hidden', t=='f');
            }

            async function processar() {
                document.getElementById('loader').classList.remove('hidden');
                const fd = new FormData();
                fd.append('nome_analise', document.getElementById('analise_nome').value || "Analise_Independente");
                fd.append('tmin_p', document.getElementById('tmin').value);
                fd.append('tmax_p', document.getElementById('tmax').value);
                fd.append('passo_p', document.getElementById('passo').value);

                if(activeTab === 'f') {
                    const fileInput = document.getElementById('arquivo');
                    if(!fileInput.files[0]) { alert("Anexe o arquivo meteorológico!"); document.getElementById('loader').classList.add('hidden'); return; }
                    fd.append('file', fileInput.files[0]);
                } else {
                    let dArr = [];
                    document.querySelectorAll('#manual-body tr').forEach(tr => {
                        const vals = Array.from(tr.querySelectorAll('input')).map(i => i.value.trim());
                        if(vals[0] && vals[1]) dArr.push(vals.join(','));
                    });
                    if(dArr.length < 3) { alert("Dados insuficientes para regressão linear."); document.getElementById('loader').classList.add('hidden'); return; }
                    fd.append('manual_data', dArr.join('\\n'));
                }

                try {
                    const response = await fetch('/api_processamento', {method:'POST', body:fd});
                    const d = await response.json();
                    if(d.detail) throw new Error(d.detail);

                    document.getElementById('results-col').classList.remove('hidden');
                    document.getElementById('v-tb').innerText = d.res.temp + "°";
                    document.getElementById('v-r2').innerText = d.res.r2.toFixed(4);
                    document.getElementById('v-qme').innerText = d.res.qme.toFixed(6);
                    document.getElementById('final-name').innerText = "🔬 Result: " + d.identidade;

                    // Plotly P&B Estilo Publicação
                    Plotly.newPlot('gr-qme', [{x:d.plt.qme_x, y:d.plt.qme_y, mode:'lines+markers', line:{color:'black'}}], {title:'Mínimo Residual QME', margin:{t:40}});
                    Plotly.newPlot('gr-reg', [{x:d.plt.reg_x, y:d.plt.reg_y, mode:'markers', marker:{color:'gray'}}, {x:d.plt.reg_x, y:d.plt.reg_pred, mode:'lines', line:{color:'black', dash:'dot'}}], {title:'Regressão: NF vs Soma Térmica', margin:{t:40}, showlegend:false});

                    window.scrollTo({top: document.body.scrollHeight, behavior:'smooth'});
                } catch(e) {
                    alert("ALERTA TÉCNICO: Falha na análise. Verifique se: \\n1. As medições da variável estão aumentando progressivamente.\\n2. Existem ao menos 3 pontos com NF informado.");
                } finally { document.getElementById('loader').classList.add('hidden'); }
            }
        </script>
    </body>
    </html>
    """.replace("CONFIG_SURL", S_URL).replace("CONFIG_SKEY", S_KEY)
    return html_content

# =========================================================================
# BACKEND: MOTOR CIENTÍFICO UNIFICADO
# =========================================================================
@app.post("/api_processamento")
async def rodar_motor_unificado(
    file: UploadFile = None, manual_data: str = Form(None),
    nome_analise: str = Form(""), tmin_p: float = Form(0.0), tmax_p: float = Form(20.0), passo_p: float = Form(0.5)
):
    try:
        # Carregamento do DF
        if file:
            c = await file.read()
            df = pd.read_csv(BytesIO(c), sep=None, engine='python', decimal=',') if file.filename.endswith('.csv') else pd.read_excel(BytesIO(c))
        else:
            df = pd.read_csv(StringIO(manual_data), names=['Data', 'Tmin', 'Tmax', 'NF'], header=None)

        # Higiene
        df = preparar_dataframe(df)
        df['Tmed'] = (df['Tmin'] + df['Tmax']) / 2
        p_df = df.dropna(subset=['NF']).copy() # Somente datas de avaliação

        results_list = []
        best_sta_data = {}
        t_base_range = np.arange(tmin_p, tmax_p + passo_p, passo_p)
        
        for tb in t_base_range:
            tb = round(float(tb), 2)
            # Soma Térmica Acumulada Diária
            std = (df['Tmed'] - tb).clip(lower=0)
            df['STa_temp'] = std.cumsum()
            
            # Seleciona STa apenas para os dias com NF
            X = df.loc[p_df.index, 'STa_temp'].values.reshape(-1, 1)
            y = p_df['NF'].values
            
            lr = LinearRegression().fit(X, y)
            r2, qme = lr.score(X,y), mean_squared_error(y, lr.predict(X))
            results_list.append({'Tb': tb, 'R2': r2, 'QME': qme, 'slope': lr.coef_[0], 'intercept': lr.intercept_})
            best_sta_data[str(tb)] = df['STa_temp'].tolist()

        res_df = pd.DataFrame(results_list)
        campeao = res_df.loc[res_df['QME'].idxmin()]
        c_str = str(round(float(campeao['Tb']), 2))
        
        idx_observado = p_df.index.tolist()
        final_sta = [best_sta_data[c_str][i] for i in range(len(df)) if i in idx_observado]

        return {
            "identidade": nome_analise,
            "res": {"temp": float(campeao['Tb']), "r2": float(campeao['R2']), "qme": float(campeao['QME'])},
            "plt": {
                "qme_x": res_df['Tb'].tolist(), "qme_y": res_df['QME'].tolist(),
                "reg_x": [float(x) for x in final_sta],
                "reg_y": p_df['NF'].astype(float).tolist(),
                "reg_pred": [(x * campeao['slope'] + campeao['intercept']) for x in final_sta]
            }
        }
    except Exception as e:
        import traceback
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))
