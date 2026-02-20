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
# CONFIGURAÇÕES (MANTER ESTAS CHAVES)
# =========================================================================
SURL = "https://iuhtopexunirguxmjiey.supabase.co"
SKEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Iml1aHRvcGV4dW5pcmd1eG1qaWV5Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzE1MjIzNTcsImV4cCI6MjA4NzA5ODM1N30.EjDui9gQ5AlRaNpoVQisGUoXmK3j74gwzq9QSguxq78"
stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "")
ADM_MAIL = "abielgm@icloud.com"

# --- AUXILIARES ---
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
    <body class="bg-slate-100 font-sans min-h-screen text-slate-800">
        <div id="loader" class="hidden fixed inset-0 bg-white/90 z-50 flex flex-col items-center justify-center italic font-black text-green-700">
            <div class="animate-spin rounded-full h-14 w-14 border-t-4 border-green-600 mb-4"></div>
            SINCRO_PROCESSAMENTO EM CURSO...
        </div>

        <div class="max-w-6xl mx-auto p-4 md:p-10">
            <!-- LOGIN -->
            <div id="login-section" class="max-w-md mx-auto bg-white p-10 rounded-[3rem] shadow-2xl mt-12 border text-center">
                <h1 class="text-4xl font-black text-green-700 italic mb-2 tracking-tighter uppercase underline decoration-yellow-400">EstimaTB🌿</h1>
                <p class="text-[9px] font-bold text-slate-300 uppercase tracking-widest mb-8 italic">Environment v1.0</p>
                <input type="email" id="email" placeholder="E-mail" class="w-full border-2 p-4 rounded-2xl mb-4 outline-none focus:border-green-600">
                <input type="password" id="password" placeholder="Senha" class="w-full border-2 p-4 rounded-2xl mb-6 outline-none focus:border-green-600">
                <button onclick="auth('login')" class="w-full bg-green-600 text-white py-4 rounded-2xl font-black shadow-lg">ENTRAR</button>
                <button onclick="toggleMode()" id="btnSw" class="text-green-600 font-bold text-[9px] uppercase mt-4 block mx-auto">Criar Cadastro Acadêmico</button>
            </div>

            <!-- DASHBOARD -->
            <div id="main-section" class="hidden animate-in fade-in duration-500">
                <div class="flex flex-col md:flex-row justify-between items-center bg-white p-6 rounded-[2rem] shadow-sm border mb-6 px-10 gap-4">
                    <p class="text-slate-400 font-bold text-xs uppercase tracking-tighter italic">Researcher: <span id="user-display" class="text-green-700 font-black not-italic ml-1"></span></p>
                    <button onclick="sair()" class="text-red-500 font-black text-[10px] uppercase underline hover:scale-105 transition-all">Sair do Sistema</button>
                </div>

                <div class="grid lg:grid-cols-12 gap-8">
                    <!-- Configurações -->
                    <div class="lg:col-span-5 bg-white p-8 rounded-[2.5rem] shadow-xl border">
                        <input type="text" id="estudo_id" placeholder="Nome do Experimento / Amostra" class="w-full border-2 p-4 rounded-2xl mb-6 bg-slate-50 text-sm font-bold focus:border-green-500 outline-none">

                        <div class="flex bg-slate-100 p-1 rounded-2xl mb-6 shadow-inner">
                            <button onclick="aba('f')" id="b-f" class="flex-1 py-3 text-[10px] font-black rounded-xl bg-white shadow text-green-700 uppercase italic">Arquivo</button>
                            <button onclick="aba('m')" id="b-m" class="flex-1 py-3 text-[10px] font-black rounded-xl text-slate-400 uppercase italic tracking-tighter">Digitação/Cola</button>
                        </div>

                        <div id="u-f" class="mb-6"><input type="file" id="arquivo" class="block w-full border-2 border-dashed p-10 rounded-2xl bg-slate-50 text-xs font-bold text-slate-400"></div>

                        <div id="u-m" class="hidden mb-6">
                            <div class="overflow-x-auto rounded-2xl border mb-2 max-h-80 shadow-inner">
                                <table class="w-full border-collapse">
                                    <thead><tr><th class="th-lab">Data</th><th class="th-lab">T-Mín</th><th class="th-lab">T-Máx</th><th class="th-lab text-green-700 italic font-black">Var (NF)</th></tr></thead>
                                    <tbody id="m-body"></tbody>
                                </table>
                            </div>
                            <div class="flex justify-between p-2"><button onclick="addR(10)" class="text-[9px] font-bold text-green-600 underline uppercase tracking-widest">+ Linhas</button><button onclick="resM()" class="text-[9px] font-bold text-red-400 uppercase italic">Limpar Tudo</button></div>
                        </div>

                        <div class="bg-slate-50 p-6 rounded-3xl border text-center grid grid-cols-3 gap-3 mb-8 shadow-inner">
                            <div class="flex flex-col"><label class="text-[8px] font-bold text-slate-400">T-MÍN</label><input type="number" id="v-min" value="0.0" class="w-full border p-2 rounded-xl text-center font-bold"></div>
                            <div class="flex flex-col"><label class="text-[8px] font-bold text-slate-400">T-MÁX</label><input type="number" id="v-max" value="20.0" class="w-full border p-2 rounded-xl text-center font-bold"></div>
                            <div class="flex flex-col"><label class="text-[8px] font-bold text-green-600 underline">PASSO</label><input type="number" id="v-step" value="0.5" step="0.1" class="w-full border p-2 rounded-xl text-center font-bold text-green-600 border-green-200"></div>
                        </div>

                        <button onclick="run()" class="w-full bg-green-600 text-white py-5 rounded-[1.8rem] font-black text-xl shadow-xl hover:scale-[1.03] transition-all uppercase tracking-widest">Processar Análise</button>
                    </div>

                    <!-- Saída -->
                    <div id="res-col" class="lg:col-span-7 hidden animate-in slide-in-from-right duration-500">
                        <div class="bg-white p-10 rounded-[3rem] shadow-2xl border-t-[14px] border-slate-900 sticky top-10">
                            <div class="grid grid-cols-3 gap-4 mb-8">
                                <div class="bg-slate-50 p-4 rounded-3xl text-center shadow-inner"><p class="text-[9px] font-black text-slate-300 italic uppercase">Temperatura Basal</p><p id="out-tb" class="text-4xl font-black font-mono tracking-tighter">--</p></div>
                                <div class="bg-slate-50 p-4 rounded-3xl text-center border-2 border-green-50 shadow-inner"><p class="text-[9px] font-black text-green-700 italic uppercase">Ajuste (R²)</p><p id="out-r2" class="text-4xl font-black font-mono text-green-600 tracking-tighter">--</p></div>
                                <div class="bg-slate-50 p-4 rounded-3xl text-center shadow-inner"><p class="text-[9px] font-black text-slate-300 italic uppercase">Min QME</p><p id="out-qme" class="text-[12px] font-bold font-mono">--</p></div>
                             </div>
                             <div class="space-y-6">
                                <div id="gr1" class="h-64 border rounded-3xl"></div>
                                <div id="gr2" class="h-64 border rounded-3xl"></div>
                             </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <script>
            const SU = "U_VAL"; const SK = "K_VAL"; const AD = "abielgm@icloud.com";
            const _supabase = supabase.createClient(SU, SK);
            let inputMode = 'f'; let loginMode = 'login';

            function resM() { document.getElementById('m-body').innerHTML = ''; addR(25); }
            function addR(n) {
                for(let i=0;i<n;i++) {
                    const tr = document.createElement('tr');
                    tr.innerHTML = '<td><input type="text" class="in-sheet dat"></td><td><input type="text" class="in-sheet tmi"></td><td><input type="text" class="in-sheet tma"></td><td><input type="text" class="in-sheet v-nf" placeholder="..."></td>';
                    document.getElementById('m-body').appendChild(tr);
                }
            }
            resM();

            // CTRL+V SUPORTE
            document.addEventListener('paste', e => {
                if(e.target.classList.contains('in-sheet')) {
                    e.preventDefault();
                    const clip = e.clipboardData.getData('text').split(/\\r?\\n/);
                    let row = e.target.closest('tr');
                    clip.forEach(txt => {
                        if(!txt.trim()) return;
                        const cells = txt.split('\\t'), ins = row.querySelectorAll('input');
                        cells.forEach((v, idx) => { if(ins[idx]) ins[idx].value = v.trim(); });
                        row = row.nextElementSibling;
                        if(!row) { addR(1); row = document.getElementById('m-body').lastElementChild; }
                    });
                }
            });

            async function auth(t) {
                const em = document.getElementById('email').value, ps = document.getElementById('password').value;
                document.getElementById('loader').classList.remove('hidden');
                let r = (t==='login') ? await _supabase.auth.signInWithPassword({email:em, password:ps}) : await _supabase.auth.signUp({email:em, password:ps});
                if(r.error) { alert("Autenticação: " + r.error.message); document.getElementById('loader').classList.add('hidden'); }
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
                sessionStorage.clear();
                window.location.replace('/'); 
            }

            function aba(t) {
                inputMode = t;
                document.getElementById('b-f').classList.toggle('bg-white', t=='f'); document.getElementById('b-m').classList.toggle('bg-white', t=='m');
                document.getElementById('u-f').classList.toggle('hidden', t=='m'); document.getElementById('u-m').classList.toggle('hidden', t=='f');
            }

            async function run() {
                document.getElementById('loader').classList.remove('hidden');
                const fd = new FormData();
                fd.append('analise', document.getElementById('estudo_id').value);
                fd.append('min', document.getElementById('v-min').value);
                fd.append('max', document.getElementById('v-max').value);
                fd.append('step', document.getElementById('v-step').value);

                if(inputMode === 'f') {
                    const f = document.getElementById('arquivo').files[0];
                    if(!f) { alert("Anexe o arquivo meteorológico!"); document.getElementById('loader').classList.add('hidden'); return; }
                    fd.append('file', f);
                } else {
                    let d = [];
                    document.querySelectorAll('#m-body tr').forEach(tr => {
                        const vals = Array.from(tr.querySelectorAll('input')).map(i => i.value.trim());
                        if(vals[0] && vals[1]) d.push(vals.join(','));
                    });
                    if(d.length < 3) { alert("Dados insuficientes para regressão."); document.getElementById('loader').classList.add('hidden'); return; }
                    fd.append('manual', d.join('\\n'));
                }

                try {
                    const res = await fetch('/api/v1/analisar', {method:'POST', body:fd});
                    const d = await res.json();
                    if(d.detail) throw new Error(d.detail);

                    document.getElementById('res-col').classList.remove('hidden');
                    document.getElementById('out-tb').innerText = d.best.temp + "°";
                    document.getElementById('out-r2').innerText = d.best.r2.toFixed(4);
                    document.getElementById('out-qme').innerText = d.best.qme.toFixed(8);

                    Plotly.newPlot('gr1', [{x: d.plt.q_x, y: d.plt.q_y, mode:'lines+markers', line:{color:'black'}}], {title:'Mínimo Residual QME (Estabilidade)', margin:{t:40}});
                    Plotly.newPlot('gr2', [{x: d.plt.r_x, y: d.plt.r_y, mode:'markers', marker:{color:'gray'}}, {x: d.plt.r_x, y: d.plt.r_p, mode:'lines', line:{color:'black', dash:'dot'}}], {title:'Modelo: NF vs STa Acumulada', showlegend:false, margin:{t:40}});
                    window.scrollTo({top: document.body.scrollHeight, behavior:'smooth'});
                } catch(e) {
                    alert(e.message || "Falha técnica nos dados.");
                } finally { document.getElementById('loader').classList.add('hidden'); }
            }
        </script>
    </body>
    </html>
    """.replace("U_VAL", SURL).replace("K_VAL", SKEY)

@app.post("/api/v1/analisar")
async def processamento_tb(
    file: UploadFile = None, manual: str = Form(None),
    analise: str = Form(""), min: float = Form(0.0), max: float = Form(20.0), step: float = Form(0.5)
):
    try:
        if file:
            content = await file.read()
            if file.filename.endswith('.csv'):
                df = pd.read_csv(BytesIO(content), sep=None, engine='python', decimal=',')
            else:
                df = pd.read_excel(BytesIO(content))
        else:
            df = pd.read_csv(StringIO(manual), names=['Data','Tmin','Tmax','NF'], header=None)

        # 1. Higiene Radical dos Dados
        df = limpar_colunas(df)
        # Forçamos a limpeza de NF: strings vazias, 'None', 'nan' viram NaN do numpy
        df['NF'] = pd.to_numeric(df['NF'].astype(str).str.replace(',', '.').replace('nan', np.nan), errors='coerce')
        df['Tmin'] = pd.to_numeric(df['Tmin'].astype(str).str.replace(',', '.'), errors='coerce')
        df['Tmax'] = pd.to_numeric(df['Tmax'].astype(str).str.replace(',', '.'), errors='coerce')
        df['Data'] = pd.to_datetime(df['Data'], dayfirst=True, errors='coerce')
        
        # Só dropamos linhas se a TEMPERATURA for vazia (precisamos delas para a Soma Térmica Acumulada)
        df = df.dropna(subset=['Data', 'Tmin', 'Tmax']).sort_values('Data')

        # Verificação se NF existe
        if df['NF'].count() < 3:
            raise ValueError(f"Foram encontradas apenas {df['NF'].count()} avaliações válidas na coluna NF/Variável. O motor precisa de no mínimo 3 pontos para a regressão.")

        # 2. Motor de Cálculo
        df['Tmed'] = (df['Tmin'] + df['Tmax']) / 2
        p_idx = df.dropna(subset=['NF']).index # Datas com avaliação
        
        results = []
        best_sta_dict = {}
        t_range = np.arange(min, max + step, step)
        
        for tb in t_range:
            tb = round(float(tb), 2)
            # Soma Térmica Acumulada: Calculamos em todos os dias (cumsum), ignorando dias onde Tmed < Tb
            std = (df['Tmed'] - tb).clip(lower=0)
            sta = std.cumsum()
            
            # Para a regressão, pegamos apenas as datas em que houve avaliação (NF)
            X = sta.loc[p_idx].values.reshape(-1, 1)
            y = df.loc[p_idx, 'NF'].values
            
            # Garantir que y não tem lixo (NaN ou Infinity)
            if np.any(np.isnan(y)): continue
            
            lr = LinearRegression().fit(X, y)
            qme = mean_squared_error(y, lr.predict(X))
            results.append({'tb': tb, 'r2': lr.score(X,y), 'qme': qme, 'a': lr.coef_[0], 'b': lr.intercept_})
            best_sta_dict[str(tb)] = sta.loc[p_idx].tolist()

        if not results:
            raise ValueError("Não foi possível realizar o cálculo. Verifique os valores de temperatura.")

        # 3. Resultado Final
        res_df = pd.DataFrame(results)
        best = res_df.loc[res_df['qme'].idxmin()]
        best_tb_str = str(round(best['tb'], 2))

        return {
            "best": {"temp": float(best['tb']), "r2": float(best['r2']), "qme": float(best['qme'])},
            "plt": {
                "q_x": res_df['tb'].tolist(), "q_y": res_df['qme'].tolist(),
                "r_x": [float(x) for x in best_sta_dict[best_tb_str]],
                "r_y": df.loc[p_idx, 'NF'].tolist(),
                "r_p": [float(x * best['a'] + best['b']) for x in best_sta_dict[best_tb_str]]
            }
        }
    except Exception as e:
        # Envia erro detalhado para o Alerta no Navegador
        import traceback
        print(traceback.format_exc())
        return {"detail": str(e)}
