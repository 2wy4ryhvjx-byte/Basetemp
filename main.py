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
# BLOCO BLINDADO - CONFIGURAÇÕES
# =========================================================================
SURL = "https://iuhtopexunirguxmjiey.supabase.co"
SKEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Iml1aHRvcGV4dW5pcmd1eG1qaWV5Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzE1MjIzNTcsImV4cCI6MjA4NzA5ODM1N30.EjDui9gQ5AlRaNpoVQisGUoXmK3j74gwzq9QSguxq78"
stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "")
ADM_MAIL = "abielgm@icloud.com"

def normalize(t):
    if not isinstance(t, str): return t
    return "".join(c for c in unicodedata.normalize('NFKD', t) if not unicodedata.combining(c)).lower().strip()

def limpar_colunas(df):
    cols = {normalize(c): c for c in df.columns}
    mapping = {'data': 'Data', 'tmin': 'Tmin', 'tmax': 'Tmax', 'nf': 'NF', 'variavel': 'NF'}
    new_cols = {}
    for k, v in mapping.items():
        for ck in cols:
            if k in ck: new_cols[cols[ck]] = v
    df.rename(columns=new_cols, inplace=True)
    return df

@app.get("/", response_class=HTMLResponse)
async def workstation():
    return """
    <!DOCTYPE html>
    <html lang="pt-br">
    <head>
        <meta charset="UTF-8"><title>EstimaTB Pro 🌿</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <script src="https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2"></script>
        <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
        <style>
            .in-sheet { width: 100%; border: 1px solid #e2e8f0; padding: 6px; font-size: 11px; text-align: center; outline: none; font-family: monospace; }
            .in-sheet:focus { background: #f0fdf4; border-color: #16a34a; }
            .th-lab { background: #f8fafc; font-size: 10px; font-weight: 900; color: #475569; padding: 10px; border: 1px solid #e2e8f0; text-transform: uppercase; }
        </style>
    </head>
    <body class="bg-slate-100 font-sans min-h-screen">
        <div id="loader" class="hidden fixed inset-0 bg-white/95 z-50 flex flex-col items-center justify-center italic font-black text-green-700">
            <div class="animate-spin rounded-full h-14 w-14 border-t-4 border-green-600 mb-4"></div>
            SINCRO_PROCESSAMENTO EM CURSO...
        </div>

        <div class="max-w-6xl mx-auto p-4 md:p-10">
            <!-- LOGIN -->
            <div id="login-section" class="max-w-md mx-auto bg-white p-10 rounded-[3rem] shadow-2xl mt-12 border text-center">
                <h1 class="text-4xl font-black text-green-700 italic mb-2 tracking-tighter uppercase underline decoration-yellow-400">EstimaTB🌿</h1>
                <p class="text-[9px] font-bold text-slate-300 uppercase tracking-widest mb-8">Professional Hub</p>
                <input type="email" id="email" placeholder="E-mail" class="w-full border-2 p-4 rounded-2xl mb-4 outline-none focus:border-green-600">
                <input type="password" id="password" placeholder="Senha" class="w-full border-2 p-4 rounded-2xl mb-6 outline-none focus:border-green-600">
                <button onclick="auth('login')" class="w-full bg-green-600 text-white py-4 rounded-2xl font-black shadow-lg hover:bg-green-700 transition">ENTRAR</button>
                <button onclick="toggleMode()" id="btnSw" class="text-green-600 font-bold text-[9px] uppercase mt-4 block mx-auto underline italic">Criar Acesso</button>
            </div>

            <!-- MAIN WORKSPACE -->
            <div id="main-section" class="hidden">
                <div class="flex flex-col md:flex-row justify-between items-center bg-white p-6 rounded-[2rem] shadow-sm border mb-6 px-10 gap-4">
                    <p class="text-slate-400 font-bold text-[10px] uppercase tracking-widest italic">Research by: <span id="user-display" class="text-green-700 not-italic font-black text-sm"></span></p>
                    <button onclick="sair()" class="text-red-500 font-black text-[10px] uppercase border border-red-100 px-4 py-1 rounded-full hover:bg-red-50 transition">Sair</button>
                </div>

                <div class="grid lg:grid-cols-12 gap-8">
                    <!-- Configurações Side -->
                    <div class="lg:col-span-5 space-y-6">
                        <div class="bg-white p-8 rounded-[2.5rem] shadow-xl border">
                            <h3 class="font-black text-slate-800 text-xs uppercase mb-6 border-b pb-4"><i class="fas fa-file-invoice mr-2 text-green-600"></i>Gestão de Amostras</h3>
                            
                            <input type="text" id="id_analise" placeholder="Identificação da Amostra" class="w-full border-2 p-4 rounded-2xl mb-6 bg-slate-50 text-sm outline-none focus:border-green-500">

                            <div class="flex bg-slate-100 p-1 rounded-2xl mb-6">
                                <button onclick="aba('f')" id="b-f" class="flex-1 py-3 text-[10px] font-black rounded-xl bg-white shadow text-green-700 uppercase">Excel Anexo</button>
                                <button onclick="aba('m')" id="b-m" class="flex-1 py-3 text-[10px] font-black rounded-xl text-slate-400 uppercase tracking-tighter italic">Colagem Manual</button>
                            </div>

                            <div id="u-f" class="mb-6"><input type="file" id="arquivo" class="block w-full border-2 border-dashed p-10 rounded-2xl bg-slate-50 text-[10px] font-bold"></div>

                            <div id="u-m" class="hidden mb-6">
                                <div class="overflow-x-auto rounded-2xl border mb-2 max-h-96 shadow-inner bg-white">
                                    <table class="w-full border-collapse">
                                        <thead><tr><th class="th-lab">Data</th><th class="th-lab">Mín</th><th class="th-lab">Máx</th><th class="th-lab italic font-black text-green-600">Variável</th></tr></thead>
                                        <tbody id="m-body"></tbody>
                                    </table>
                                </div>
                                <div class="flex justify-between px-2 mb-4">
                                    <button onclick="addR(5)" class="text-[9px] font-bold text-green-600 hover:underline uppercase">+ Linhas</button>
                                    <button onclick="resM()" class="text-[9px] font-bold text-slate-400 hover:text-red-500 uppercase">Zerar Planilha</button>
                                </div>
                            </div>

                            <div class="bg-slate-50 p-6 rounded-3xl border text-center grid grid-cols-3 gap-3 mb-8">
                                <div class="flex flex-col"><label class="text-[8px] font-black uppercase text-slate-400">Faixa Mín</label><input type="number" id="vmin" value="0.0" class="w-full border p-2 rounded-xl text-center font-bold text-xs"></div>
                                <div class="flex flex-col"><label class="text-[8px] font-black uppercase text-slate-400">Faixa Máx</label><input type="number" id="vmax" value="20.0" class="w-full border p-2 rounded-xl text-center font-bold text-xs"></div>
                                <div class="flex flex-col"><label class="text-[8px] font-bold uppercase text-green-700">Passo</label><input type="number" id="vstep" value="0.5" step="0.1" class="w-full border p-2 rounded-xl text-center font-bold text-xs text-green-700 border-green-200"></div>
                            </div>

                            <button onclick="executar()" id="btnCal" class="w-full bg-green-600 text-white py-5 rounded-[1.8rem] font-black text-xl shadow-xl hover:bg-green-700 uppercase tracking-tighter italic">Gerar Modelagem</button>
                        </div>
                    </div>

                    <!-- Gráficos Principal -->
                    <div id="res-col" class="lg:col-span-7 hidden animate-in slide-in-from-right">
                        <div class="bg-white p-10 rounded-[3rem] shadow-2xl border-t-[14px] border-slate-900 sticky top-6">
                            <h2 class="text-xl font-black italic border-b pb-4 mb-10 text-slate-800" id="h-id">Laboratório de Análise</h2>
                             <div class="grid grid-cols-3 gap-4 mb-10">
                                <div class="bg-slate-50 p-6 rounded-3xl border text-center shadow-inner italic"><p class="text-[9px] font-black text-slate-300 block mb-1">Temperatura Basal</p><p id="out-tb" class="text-4xl font-black font-mono">--</p></div>
                                <div class="bg-slate-50 p-6 rounded-3xl border border-green-50 text-center shadow-inner"><p class="text-[9px] font-black text-green-600 block mb-1 uppercase tracking-tighter">Ajuste (R²)</p><p id="out-r2" class="text-4xl font-black font-mono text-green-700 tracking-tight">--</p></div>
                                <div class="bg-slate-50 p-6 rounded-3xl border text-center shadow-inner"><p class="text-[9px] font-black text-slate-300 block mb-1">Mínimo QME</p><p id="out-qme" class="text-xs font-bold font-mono">--</p></div>
                             </div>
                             
                             <div class="space-y-6">
                                <div id="plt1" class="h-64 border rounded-2xl bg-white shadow-inner"></div>
                                <div id="plt2" class="h-64 border rounded-2xl bg-white shadow-inner"></div>
                             </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <script>
            const SU = "S_VAL_URL"; const SK = "S_VAL_KEY"; const MASTER_ID = "abielgm@icloud.com";
            const _supabase = supabase.createClient(SU, SK);
            let mTab = 'f'; let loginMode = 'login';

            function resM() { document.getElementById('m-body').innerHTML = ''; addR(15); }
            function addR(n) {
                const b = document.getElementById('m-body');
                for(let i=0; i<n; i++) {
                    const tr = document.createElement('tr');
                    tr.innerHTML = '<td><input type="text" class="in-sheet dat"></td><td><input type="text" class="in-sheet tmi"></td><td><input type="text" class="in-sheet tma"></td><td><input type="text" class="in-sheet var_f" placeholder="..."></td>';
                    b.appendChild(tr);
                }
            }
            resM();

            // FUNÇÃO COLAR SUPREMADO: Ignora colunas extras do Excel
            document.addEventListener('paste', function(e) {
                if(e.target.classList.contains('in-sheet')) {
                    e.preventDefault();
                    const clipText = e.clipboardData.getData('text');
                    const clipRows = clipText.split(/\\r?\\n/);
                    let rowTr = e.target.closest('tr');
                    
                    clipRows.forEach(rowString => {
                        if(rowString.trim() === '') return;
                        const cellData = rowString.split('\\t');
                        const inputs = rowTr.querySelectorAll('input');
                        // SÓ PEGA AS 4 PRIMEIRAS COLUNAS PARA EVITAR "EXTRA FIELDS"
                        for(let i=0; i < Math.min(4, cellData.length, inputs.length); i++) {
                            // Limpa e normaliza: troca vírgula decimal por ponto no envio
                            let val = cellData[i].trim().replace(',', '.');
                            inputs[i].value = val;
                        }
                        rowTr = rowTr.nextElementSibling;
                        if(!rowTr && clipRows.length > 0) { addR(1); rowTr = document.getElementById('m-body').lastElementChild; }
                    });
                }
            });

            async function auth(t) {
                const em = document.getElementById('email').value, pw = document.getElementById('password').value;
                document.getElementById('loader').classList.remove('hidden');
                let r = (t === 'login') ? await _supabase.auth.signInWithPassword({email:em, password:pw}) : await _supabase.auth.signUp({email:em, password:pw});
                if(r.error) { alert("Ops! " + r.error.message); document.getElementById('loader').classList.add('hidden'); }
                else location.reload();
            }

            async function checkS() {
                const {data:{user}} = await _supabase.auth.getUser();
                if(user) {
                    document.getElementById('login-section').classList.add('hidden');
                    document.getElementById('main-section').classList.remove('hidden');
                    document.getElementById('user-display').innerText = user.email.toLowerCase();
                }
            }
            checkS();
            async function sair() { 
                await _supabase.auth.signOut();
                localStorage.clear();
                window.location.replace('/'); 
            }

            function aba(m) {
                mTab = m;
                document.getElementById('b-f').classList.toggle('bg-white', m=='f');
                document.getElementById('b-m').classList.toggle('bg-white', m=='m');
                document.getElementById('u-f').classList.toggle('hidden', m=='m');
                document.getElementById('u-m').classList.toggle('hidden', m=='f');
            }

            async function executar() {
                document.getElementById('loader').classList.remove('hidden');
                const fd = new FormData();
                fd.append('nome_e', document.getElementById('id_analise').value);
                fd.append('p_min', document.getElementById('vmin').value);
                fd.append('p_max', document.getElementById('vmax').value);
                fd.append('p_step', document.getElementById('vstep').value);

                if(mTab === 'f') {
                    const fl = document.getElementById('arquivo').files[0];
                    if(!fl) { alert("Escolha o arquivo científico!"); document.getElementById('loader').classList.add('hidden'); return; }
                    fd.append('file', fl);
                } else {
                    let rowsText = [];
                    document.querySelectorAll('#m-body tr').forEach(tr => {
                        // Capturamos exatamente os 4 campos para evitar tokenization error
                        const cells = Array.from(tr.querySelectorAll('input')).map(i => i.value.trim().replace(',', '.'));
                        if(cells[0] && cells[1] && cells[2]) {
                            // Se a variável estiver vazia, garantimos que enviamos "nan"
                            if(!cells[3]) cells[3] = 'nan';
                            rowsText.push(cells.join(','));
                        }
                    });
                    if(rowsText.length < 5) { alert("Planilha insuficiente!"); document.getElementById('loader').classList.add('hidden'); return; }
                    fd.append('manual', rowsText.join('\\n'));
                }

                try {
                    const resp = await fetch('/api/analise', {method:'POST', body:fd});
                    const d = await resp.json();
                    if(d.detail) throw new Error(d.detail);

                    document.getElementById('res-col').classList.remove('hidden');
                    document.getElementById('out-tb').innerText = d.best.t + "°";
                    document.getElementById('out-r2').innerText = d.best.r2.toFixed(4);
                    document.getElementById('out-qme').innerText = d.best.qme.toFixed(8);
                    document.getElementById('h-id').innerText = d.analise || "Análise de Estabilidade";

                    Plotly.newPlot('plt1', [{x: d.plt.qx, y: d.plt.qy, mode: 'lines+markers', line:{color:'black'}}], {title:'Gráfico de Residual QME', font:{size:10}, margin:{t:40}});
                    Plotly.newPlot('plt2', [{x: d.plt.rx, y: d.plt.ry, mode: 'markers', marker:{color:'gray'}, name:'Obs.'},{x: d.plt.rx, y: d.plt.rp, mode: 'lines', line:{color:'black', dash:'dot'}}], {title:'Regressão: NF vs STa', font:{size:10}, showlegend:false, margin:{t:40}});
                    window.scrollTo({top: document.body.scrollHeight, behavior:'smooth'});
                } catch(e) {
                    alert(e.message || "Verifique as datas (DD/MM/AAAA) e certifique-se que NF tem medições.");
                } finally { document.getElementById('loader').classList.add('hidden'); }
            }
        </script>
    </body>
    </html>
    """.replace("S_VAL_URL", SURL).replace("S_VAL_KEY", SKEY)

@app.post("/api/analise")
async def processamento(
    file: UploadFile = None, manual: str = Form(None),
    nome_e: str = Form(""), p_min: float = Form(0.0), p_max: float = Form(20.0), p_step: float = Form(0.5)
):
    try:
        if file:
            c = await file.read()
            df = pd.read_csv(BytesIO(c), sep=None, engine='python', decimal=',') if file.filename.endswith('.csv') else pd.read_excel(BytesIO(c))
        else:
            # Forçamos o separador de colunas a ser a vírgula para coincidir com o JOIN do JS
            df = pd.read_csv(StringIO(manual), sep=',', names=['Data','Tmin','Tmax','NF'], header=None, on_bad_lines='skip')

        # 1. Higienização para o Motor Científico
        df = limpar_colunas(df)
        df['NF'] = pd.to_numeric(df['NF'].astype(str).str.replace(',', '.'), errors='coerce')
        df['Tmin'] = pd.to_numeric(df['Tmin'].astype(str).str.replace(',', '.'), errors='coerce')
        df['Tmax'] = pd.to_numeric(df['Tmax'].astype(str).str.replace(',', '.'), errors='coerce')
        df['Data'] = pd.to_datetime(df['Data'], dayfirst=True, errors='coerce')
        
        # Manter dados diários de clima mas ordenar
        df = df.dropna(subset=['Data','Tmin','Tmax']).sort_values('Data')

        # Verificação NF
        valid_nf = df.dropna(subset=['NF'])
        if len(valid_nf) < 3:
            raise ValueError(f"Foram identificados apenas {len(valid_nf)} pontos com a 'Variável' preenchida. Cole mais linhas com avaliações para realizar a regressão.")

        # 2. Cálculos Agrometeorológicos
        df['Tmed'] = (df['Tmin'] + df['Tmax']) / 2
        p_idx = valid_nf.index
        
        scores = []
        best_sta_track = {}
        t_list = np.arange(p_min, p_max + p_step, p_step)

        for tb in t_list:
            tb = round(float(tb), 2)
            # Soma Térmica (Cálculo do dia i - Tb) -> Cumulativo
            sta_serie = (df['Tmed'] - tb).clip(lower=0).cumsum()
            
            X = sta_serie.loc[p_idx].values.reshape(-1, 1)
            y = df.loc[p_idx, 'NF'].values
            
            lr = LinearRegression().fit(X, y)
            qme = mean_squared_error(y, lr.predict(X))
            scores.append({'tb': tb, 'r2': lr.score(X,y), 'qme': qme, 'm': lr.coef_[0], 'i': lr.intercept_})
            best_sta_track[str(tb)] = sta_serie.loc[p_idx].tolist()

        rdf = pd.DataFrame(scores)
        bt = rdf.loc[rdf['qme'].idxmin()]
        bt_s = str(round(float(bt['tb']), 2))

        return {
            "analise": nome_e,
            "best": {"t": float(bt['tb']), "r2": float(bt['r2']), "qme": float(bt['qme'])},
            "plt": {
                "qx": rdf['tb'].tolist(), "qy": rdf['qme'].tolist(),
                "rx": [float(x) for x in best_sta_track[bt_s]],
                "ry": df.loc[p_idx, 'NF'].tolist(),
                "rp": [float(x * bt['m'] + bt['i']) for x in best_sta_track[bt_s]]
            }
        }
    except Exception as e:
        return {"detail": str(e)}
