import os
import stripe
import pandas as pd
import numpy as np
from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from fastapi.responses import HTMLResponse
from io import BytesIO, StringIO
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_squared_error
import unicodedata

app = FastAPI()

# =========================================================================
# BLOCO DE SEGURANÇA E CONFIGURAÇÃO (NÃO MODIFICAR)
# =========================================================================
S_URL = "https://iuhtopexunirguxmjiey.supabase.co"
S_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Iml1aHRvcGV4dW5pcmd1eG1qaWV5Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzE1MjIzNTcsImV4cCI6MjA4NzA5ODM1N30.EjDui9gQ5AlRaNpoVQisGUoXmK3j74gwzq9QSguxq78"
stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "")
EMAIL_ADMIN = "abielgm@icloud.com"

# --- FUNÇÕES DE SUPORTE CIENTÍFICO (IGUAL AO SEU CÓDIGO STREAMLIT) ---
def normalize_text(text):
    if not isinstance(text, str): return text
    text = "".join(c for c in unicodedata.normalize('NFKD', text) if not unicodedata.combining(c))
    return text.lower().replace(" ", "").replace("_", "")

def rename_columns_cientifico(df):
    COLUMN_MAP = {'data': 'Data', 'tmin': 'Tmin', 'tmín': 'Tmin', 'tmax': 'Tmax', 'tmáx': 'Tmax', 'nf': 'NF', 'variavel': 'NF'}
    df.rename(columns=lambda col: COLUMN_MAP.get(normalize_text(col), col), inplace=True)
    return df

@app.get("/", response_class=HTMLResponse)
async def interface():
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
            .excel-cell { width: 100%; border: 1px solid #e2e8f0; padding: 4px; font-size: 11px; text-align: center; font-family: monospace; outline: none; }
            .excel-cell:focus { background-color: #f0fdf4; border: 1px solid #16a34a; }
            .th-lab { background: #f8fafc; font-size: 10px; font-weight: 900; color: #475569; padding: 8px; border: 1px solid #e2e8f0; text-transform: uppercase; }
        </style>
    </head>
    <body class="bg-slate-50 font-sans min-h-screen text-slate-800">
        
        <div id="loader" class="hidden fixed inset-0 bg-white/95 flex items-center justify-center z-50 flex-col">
            <div class="animate-spin rounded-full h-14 w-14 border-t-2 border-b-2 border-green-700 mb-4"></div>
            <p class="font-black text-green-900 animate-pulse uppercase tracking-tighter">Motor Científico Processando...</p>
        </div>

        <div class="max-w-6xl mx-auto p-4 md:p-10">
            <!-- TELA LOGIN -->
            <div id="login-section" class="max-w-md mx-auto bg-white p-10 rounded-[2.5rem] shadow-2xl mt-12 text-center border">
                <h1 class="text-4xl font-black text-green-700 italic mb-1 italic">EstimaTB🌿</h1>
                <p class="text-[9px] font-bold text-slate-300 uppercase tracking-widest mb-8">Calculadora Agrometeorológica</p>
                <div class="space-y-4">
                    <input type="email" id="email" placeholder="E-mail" class="w-full border-2 p-4 rounded-2xl outline-none focus:border-green-600 bg-slate-50">
                    <input type="password" id="password" placeholder="Senha" class="w-full border-2 p-4 rounded-2xl outline-none focus:border-green-600 bg-slate-50">
                    <button onclick="auth('login')" id="btnLogin" class="w-full bg-green-600 text-white py-4 rounded-2xl font-black shadow-lg">ENTRAR</button>
                    <button onclick="toggleMode()" id="btnSwitch" class="text-green-600 font-bold text-[10px] uppercase mt-2">Cadastro</button>
                </div>
            </div>

            <!-- TELA WORKSTATION -->
            <div id="main-section" class="hidden">
                <div class="flex justify-between items-center bg-white p-6 rounded-[2rem] shadow-sm border mb-8 px-10">
                    <p class="text-slate-400 font-bold text-xs italic italic">Researcher: <span id="user-display" class="text-green-700 font-black not-italic uppercase tracking-tighter"></span></p>
                    <button onclick="logout()" class="text-red-500 font-black text-[10px] uppercase underline transition-all">Sair</button>
                </div>

                <div class="grid grid-cols-1 lg:grid-cols-12 gap-8">
                    <!-- Configurações e Inputs -->
                    <div class="lg:col-span-5 space-y-6">
                        <div class="bg-white p-8 rounded-[2.5rem] shadow-xl border relative">
                            <h3 class="font-black text-slate-800 text-[10px] uppercase mb-6 flex items-center border-b pb-4 italic"><i class="fas fa-microscope mr-2 text-green-600"></i>Configurações do Estudo</h3>
                            
                            <input type="text" id="analise_nome" placeholder="Nome da Análise (Ex: Milho Safrinha)" class="w-full border-2 p-4 rounded-2xl mb-6 bg-slate-50 text-sm font-bold focus:border-green-600 outline-none shadow-inner">

                            <div class="flex bg-slate-100 p-1 rounded-2xl mb-6 shadow-inner">
                                <button onclick="setTab('f')" id="tab-f" class="flex-1 py-3 text-[10px] font-black rounded-xl bg-white shadow text-green-700 uppercase">Arquivo Anexo</button>
                                <button onclick="setTab('m')" id="tab-m" class="flex-1 py-3 text-[10px] font-black rounded-xl text-slate-400 uppercase tracking-tighter italic">Colar Excel</button>
                            </div>

                            <div id="ui-f" class="mb-6">
                                <input type="file" id="arquivo" class="block w-full border-2 border-dashed p-10 rounded-2xl bg-slate-50 cursor-pointer">
                                <p class="text-[9px] text-center text-slate-400 mt-2">Colunas: Data | Tmin | Tmax | Variável</p>
                            </div>

                            <div id="ui-m" class="hidden">
                                <div class="bg-white rounded-xl border overflow-hidden shadow-inner mb-4 max-h-80 overflow-y-auto">
                                    <table class="w-full border-collapse" id="spreadsheet">
                                        <thead>
                                            <tr>
                                                <th class="th-lab">Data</th>
                                                <th class="th-lab">Min</th>
                                                <th class="th-lab">Max</th>
                                                <th class="th-lab">Variável</th>
                                            </tr>
                                        </thead>
                                        <tbody id="manual-body"></tbody>
                                    </table>
                                </div>
                                <div class="flex justify-between items-center mb-6">
                                    <button onclick="addRow(5)" class="text-[9px] font-black text-green-600 hover:underline uppercase">+ Linhas</button>
                                    <button onclick="initManual()" class="text-[9px] font-black text-red-500 hover:underline uppercase">Limpar</button>
                                </div>
                            </div>

                            <div class="bg-slate-50 p-6 rounded-3xl mt-4 border shadow-inner text-center">
                                <p class="text-[9px] font-black text-slate-400 uppercase mb-4 tracking-tighter">Faixa de Estudo e Passo</p>
                                <div class="grid grid-cols-3 gap-2">
                                    <div><label class="text-[8px] font-bold block">Min</label><input type="number" id="tmin" value="0.0" class="w-full border p-2 rounded-xl text-center font-bold text-sm"></div>
                                    <div><label class="text-[8px] font-bold block">Max</label><input type="number" id="tmax" value="20.0" class="w-full border p-2 rounded-xl text-center font-bold text-sm"></div>
                                    <div><label class="text-[8px] font-bold block">Passo</label><input type="number" id="passo" value="0.5" step="0.1" class="w-full border p-2 rounded-xl text-center font-bold text-sm text-green-700"></div>
                                </div>
                            </div>

                            <button onclick="rodarCalculo()" id="btnCalc" class="mt-8 w-full bg-green-600 text-white py-5 rounded-[1.5rem] font-black text-xl shadow-xl hover:scale-[1.03] transition-all">ANALISAR CAMPO</button>
                        </div>
                    </div>

                    <!-- Saída Gráfica -->
                    <div id="results-view" class="lg:col-span-7 hidden">
                        <div class="bg-white p-10 rounded-[3rem] shadow-2xl border-t-[12px] border-slate-900 sticky top-4">
                             <h2 class="text-xl font-black italic border-b pb-4 mb-10 text-slate-800" id="exibir-nome">Relatório da Época</h2>
                             <div class="grid grid-cols-3 gap-4 mb-10">
                                <div class="bg-slate-50 p-6 rounded-3xl border text-center shadow-inner"><span class="text-[10px] font-black text-slate-400 italic block mb-1">Temperatura Basal</span><p id="r-tb" class="text-4xl font-black font-mono">--</p></div>
                                <div class="bg-slate-50 p-6 rounded-3xl border border-green-50 text-center shadow-inner"><span class="text-[10px] font-black text-green-600 block mb-1">Ajuste R²</span><p id="r-r2" class="text-4xl font-black font-mono text-green-600">--</p></div>
                                <div class="bg-slate-50 p-6 rounded-3xl border text-center shadow-inner"><span class="text-[10px] font-black text-slate-400 block mb-1 uppercase tracking-tighter">Min QME</span><p id="r-qme" class="text-[14px] font-bold font-mono">--</p></div>
                             </div>
                             
                             <div class="space-y-8">
                                <div id="plt-qme" class="h-64 border-2 rounded-2xl shadow-inner bg-white"></div>
                                <div id="plt-reg" class="h-64 border-2 rounded-2xl shadow-inner bg-white"></div>
                             </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <script>
            const S_URL = "SURL_V"; const S_KEY = "SKEY_V"; const ADM_ID = "abielgm@icloud.com";
            const _supabase = supabase.createClient(S_URL, S_KEY);
            let inputTab = 'f';

            function initManual() { 
                document.getElementById('manual-body').innerHTML = ''; addRow(15); 
            }
            function addRow(n) {
                for(let i=0; i<n; i++) {
                    const tr = document.createElement('tr');
                    tr.innerHTML = '<td><input type="text" class="excel-cell d-in"></td><td><input type="text" class="excel-cell tmi-in"></td><td><input type="text" class="excel-cell tma-in"></td><td><input type="text" class="excel-cell var-in"></td>';
                    document.getElementById('manual-body').appendChild(tr);
                }
            }
            initManual();

            // CTRL+V DO EXCEL
            document.addEventListener('paste', function(e) {
                if(e.target.classList.contains('excel-cell')) {
                    e.preventDefault();
                    const clipboard = e.clipboardData.getData('text');
                    const lines = clipboard.split(/\\r?\\n/);
                    let rowTr = e.target.closest('tr');
                    lines.forEach(lineText => {
                        if(lineText.trim()==='') return;
                        const data = lineText.split('\\t');
                        const inputs = rowTr.querySelectorAll('input');
                        data.forEach((val, i) => { if(inputs[i]) inputs[i].value = val.trim(); });
                        rowTr = rowTr.nextElementSibling;
                        if(!rowTr) { addRow(1); rowTr = document.getElementById('manual-body').lastElementChild; }
                    });
                }
            });

            async function auth(t) {
                const em = document.getElementById('email').value, pw = document.getElementById('password').value;
                document.getElementById('loader').classList.remove('hidden');
                let r = (t === 'login') ? await _supabase.auth.signInWithPassword({email: em, password: pw}) : await _supabase.auth.signUp({email: em, password: pw});
                if(r.error) { alert("Ops! Credenciais incorretas."); document.getElementById('loader').classList.add('hidden'); }
                else location.reload();
            }

            async function checkUser() {
                const {data:{user}} = await _supabase.auth.getUser();
                if(user) {
                    document.getElementById('login-section').classList.add('hidden');
                    document.getElementById('main-section').classList.remove('hidden');
                    document.getElementById('user-display').innerText = user.email.toLowerCase();
                    if(user.email.toLowerCase() === ADM_ID) document.querySelectorAll('.adm-hidden').forEach(el => el.classList.remove('hidden'));
                }
            }
            checkUser();
            async function logout() { await _supabase.auth.signOut(); localStorage.clear(); window.location.replace('/'); }

            function setTab(m) {
                inputTab = m;
                document.getElementById('tab-f').classList.toggle('bg-white', m=='f'); document.getElementById('tab-m').classList.toggle('bg-white', m=='m');
                document.getElementById('ui-f').classList.toggle('hidden', m=='m'); document.getElementById('ui-m').classList.toggle('hidden', m=='f');
            }

            async function rodarCalculo() {
                document.getElementById('loader').classList.remove('hidden');
                const fd = new FormData();
                fd.append('analise', document.getElementById('analise_nome').value);
                fd.append('tmin_p', document.getElementById('tmin').value);
                fd.append('tmax_p', document.getElementById('tmax').value);
                fd.append('passo_p', document.getElementById('passo').value);

                if(inputTab === 'f') {
                    const f = document.getElementById('arquivo').files[0];
                    if(!f) { alert("Falta o arquivo de entrada!"); document.getElementById('loader').classList.add('hidden'); return; }
                    fd.append('file', f);
                } else {
                    let dTable = [];
                    document.querySelectorAll('#manual-body tr').forEach(tr => {
                        const vals = Array.from(tr.querySelectorAll('input')).map(i => i.value.trim());
                        if(vals[0] && vals[1]) dTable.push(vals.join(','));
                    });
                    if(dTable.length < 5) { alert("Dados insuficientes na planilha manual."); document.getElementById('loader').classList.add('hidden'); return; }
                    fd.append('manual_data', dTable.join('\\n'));
                }

                try {
                    const response = await fetch('/calcular_cientifico', {method:'POST', body:fd});
                    const d = await response.json();
                    if(d.detail) throw new Error(d.detail);

                    document.getElementById('results-view').classList.remove('hidden');
                    document.getElementById('exibir-nome').innerText = "🔬 Result: " + (d.nome || "Indefinida");
                    document.getElementById('r-tb').innerText = d.best.temp + "°";
                    document.getElementById('r-r2').innerText = d.best.r2.toFixed(4);
                    document.getElementById('r-qme').innerText = d.best.qme.toFixed(6);

                    Plotly.newPlot('gr-qme', [{x: d.plt.qme_x, y: d.plt.qme_y, mode: 'lines+markers', line:{color:'black'}, marker:{color:'black'}}], {title:'Mínimo Residual QME', font:{size:10}});
                    Plotly.newPlot('gr-reg', [{x: d.plt.reg_x, y: d.plt.reg_y, mode: 'markers', marker:{color:'gray'}, name:'Dado'},{x: d.plt.reg_x, y: d.plt.reg_pred, mode: 'lines', line:{color:'black', dash:'dot'}, name:'Regressão'}], {title:'Regressão Linear STa vs NF', font:{size:10}, showlegend:false});

                    window.scrollTo({top: document.body.scrollHeight, behavior:'smooth'});
                } catch(e) { 
                    alert("ALERTA CIENTÍFICO: Falha no processamento. Verifique se os dados de NF/Variável estão aumentando progressivamente conforme os dias.");
                } finally { document.getElementById('loader').classList.add('hidden'); }
            }
        </script>
    </body>
    </html>
    """.replace("SURL_V", S_URL).replace("SKEY_V", S_KEY)
    return html_raw

# --- BACKEND (LOGICA ORIGINAL TRANSCRITA PARA O SaaS) ---
@app.post("/calcular_cientifico")
async def processar_tb(
    file: UploadFile = None, manual_data: str = Form(None),
    analise: str = Form(""), tmin_p: float = Form(0.0), tmax_p: float = Form(20.0), passo_p: float = Form(0.5)
):
    try:
        # Carregamento do DataFrame (Suporta colunas Data, Tmin, Tmax, NF)
        if file:
            c = await file.read()
            df = pd.read_csv(BytesIO(c), sep=None, engine='python', decimal=',') if file.filename.endswith('.csv') else pd.read_excel(BytesIO(c))
        else:
            df = pd.read_csv(StringIO(manual_data), names=['Data','Tmin','Tmax','NF'], header=None)

        # Higiene de Colunas e Datas (Baseado no seu load_and_validate_data)
        df = rename_columns_cientifico(df)
        df['Data'] = pd.to_datetime(df['Data'], dayfirst=True, errors='coerce')
        for c in ['Tmin','Tmax','NF']: df[c] = pd.to_numeric(df[c].astype(str).str.replace(',','.').replace('nan', np.nan), errors='coerce')
        
        df = df.dropna(subset=['Data','Tmin','Tmax']).sort_values('Data')

        # --- Lógica Original do perform_analysis ---
        df['Tmed'] = (df['Tmin'] + df['Tmax']) / 2
        pheno_df = df.dropna(subset=['NF']).copy() # Apenas onde há avaliação de campo

        results = []
        # Tabela auxiliar para STa
        sta_matrix = {}
        base_temps = np.arange(tmin_p, tmax_p + passo_p, passo_p)
        
        for tb in base_temps:
            tb = round(tb, 2)
            tb_str = str(tb)
            # Soma Térmica Diária (zera negativos como no original)
            std = df['Tmed'] - tb
            std.clip(lower=0, inplace=True)
            df['STa_calculada'] = std.cumsum()
            
            # Dados para a regressão apenas nos dias avaliados
            X = df.loc[pheno_df.index, 'STa_calculada'].values.reshape(-1,1)
            y = pheno_df['NF'].values
            
            model = LinearRegression().fit(X, y)
            preds = model.predict(X)
            qme = mean_squared_error(y, preds)
            r2 = model.score(X,y)
            
            results.append({'Tb': tb, 'R2': r2, 'QME': qme, 'ang': model.coef_[0], 'int': model.intercept_})
            sta_matrix[tb_str] = df['STa_calculada'].tolist()

        qme_df = pd.DataFrame(results)
        best = qme_df.loc[qme_df['QME'].idxmin()]
        best_tb_str = str(round(best['Tb'], 2))

        # Gerar arrays para gráficos Plotly
        idx_pheno = pheno_df.index.tolist()
        sta_v = [sta_matrix[best_tb_str][i] for i in range(len(df)) if i in idx_pheno]
        
        return {
            "nome": analise,
            "best": {"temp": float(best['Tb']), "r2": float(best['R2']), "qme": float(best['QME'])},
            "plt": {
                "qme_x": qme_df['Tb'].tolist(), "qme_y": qme_df['QME'].tolist(),
                "reg_x": [float(x) for x in sta_v],
                "reg_y": pheno_df['NF'].astype(float).tolist(),
                "reg_pred": [(x * best['ang'] + best['int']) for x in sta_v]
            }
        }
    except Exception as e:
        return {"detail": str(e)}
