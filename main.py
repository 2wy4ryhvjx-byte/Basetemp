import os
import stripe
import pandas as pd
import numpy as np
import unicodedata
import base64
from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from fastapi.responses import HTMLResponse
from io import BytesIO, StringIO
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_squared_error

app = FastAPI()

# =========================================================================
# 🔒 BLOCO 1: LOGIN E SEGURANÇA (BLINDADO)
# =========================================================================
SURL = "https://iuhtopexunirguxmjiey.supabase.co"
SKEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Iml1aHRvcGV4dW5pcmd1eG1qaWV5Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzE1MjIzNTcsImV4cCI6MjA4NzA5ODM1N30.EjDui9gQ5AlRaNpoVQisGUoXmK3j74gwzq9QSguxq78"
stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "")
ADM_MAIL = "abielgm@icloud.com"

# =========================================================================
# 🧬 BLOCO 2: MOTOR CIENTÍFICO E EXCEL (AUTO-SUFICIENTE)
# =========================================================================
def clean_txt(t):
    if not isinstance(t, str): return t
    return "".join(c for c in unicodedata.normalize('NFKD', t) if not unicodedata.combining(c)).lower().strip()

def fix_cols(df):
    m = {'data': 'Data', 'tmin': 'Tmin', 'tmín': 'Tmin', 'tmax': 'Tmax', 'tmáx': 'Tmax', 'nf': 'NF', 'variavel': 'NF'}
    new = {}
    for c in df.columns:
        norm = clean_txt(c)
        if norm in m: new[c] = m[norm]
    return df.rename(columns=new)

def gerar_xlsx_b64(df_clima, df_erros, df_regressao, melhor_tb):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df_clima.to_excel(writer, sheet_name='Meteorologia_Diaria', index=False)
        df_regressao.to_excel(writer, sheet_name='NF_vs_STa', index=False)
        df_erros.to_excel(writer, sheet_name='Resultados_QME', index=False)
        
        # Estética do Excel
        wb = writer.book
        fmt_date = wb.add_format({'num_format': 'dd/mm/yyyy'})
        ws = writer.sheets['NF_vs_STa']
        ws.set_column('A:A', 12, fmt_date)
        
        # Gráfico QME embutido no arquivo
        chart = wb.add_chart({'type': 'scatter', 'subtype': 'smooth'})
        chart.add_series({
            'name': 'Curva de Estabilidade',
            'categories': ['Resultados_QME', 1, 0, len(df_erros), 0],
            'values':     ['Resultados_QME', 1, 2, len(df_erros), 2],
        })
        chart.set_title({'name': f'Temperatura Basal Estimada: {melhor_tb}°C'})
        writer.sheets['Resultados_QME'].insert_chart('E2', chart)
        
    return base64.b64encode(output.getvalue()).decode()

# =========================================================================
# 🎨 BLOCO 3: INTERFACE DE LABORATÓRIO (MODERNA)
# =========================================================================
@app.get("/", response_class=HTMLResponse)
async def workstation():
    html = """
    <!DOCTYPE html>
    <html lang="pt-br">
    <head>
        <meta charset="UTF-8"><title>EstimaTB Pro 🌿</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <script src="https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2"></script>
        <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
        <style>
            .sheet-cell { width: 100%; border: 1px solid #e2e8f0; padding: 6px; font-size: 11px; text-align: center; outline: none; font-family: monospace; }
            .sheet-cell:focus { background-color: #f0fdf4; border: 2px solid #16a34a; }
            .th-lab { background: #f8fafc; font-size: 9px; font-weight: 900; color: #64748b; padding: 12px; border: 1px solid #e2e8f0; text-transform: uppercase; }
        </style>
    </head>
    <body class="bg-slate-50 font-sans min-h-screen text-slate-800">
        <div id="loader" class="hidden fixed inset-0 bg-white/95 z-50 flex flex-col items-center justify-center italic font-black text-green-700">
            <div class="animate-spin rounded-full h-16 w-16 border-t-4 border-green-600 mb-4"></div>
            AGRO-ALGORITMO EM PROCESSAMENTO...
        </div>

        <div class="max-w-6xl mx-auto p-4 md:p-10">
            <!-- LOGIN SECTION -->
            <div id="login-section" class="max-w-md mx-auto bg-white p-12 rounded-[3rem] shadow-2xl mt-12 border text-center">
                <h1 class="text-5xl font-black text-green-700 italic mb-2 tracking-tighter uppercase underline decoration-yellow-400">EstimaTB🌿</h1>
                <p class="text-[10px] font-bold text-slate-300 uppercase tracking-widest mb-10 italic">Academic Workspace v1.1</p>
                <input type="email" id="email" placeholder="E-mail Acadêmico" class="w-full border-2 p-4 rounded-3xl outline-none focus:border-green-600 bg-slate-50 mb-4 shadow-inner text-sm">
                <input type="password" id="password" placeholder="Sua Senha" class="w-full border-2 p-4 rounded-3xl outline-none focus:border-green-600 bg-slate-50 mb-8 shadow-inner text-sm">
                <button onclick="auth('login')" class="w-full bg-green-600 text-white py-4 rounded-3xl font-black shadow-xl hover:bg-green-700 active:scale-95 transition tracking-widest uppercase">Entrar no Lab</button>
                <button onclick="toggleM()" id="sw" class="text-green-600 font-bold text-[9px] uppercase mt-6 block mx-auto underline tracking-widest italic">Solicitar Nova Credencial</button>
            </div>

            <!-- MAIN SECTION -->
            <div id="main-section" class="hidden animate-in fade-in duration-700">
                <div class="flex flex-col md:flex-row justify-between items-center bg-white p-6 rounded-[2.5rem] shadow-sm border mb-8 px-10 gap-4">
                    <p class="text-slate-400 font-bold text-[10px] uppercase tracking-widest italic italic">Logged Scholar: <span id="user-display" class="text-green-700 not-italic font-black text-sm ml-1"></span></p>
                    <div id="tag-m" class="hidden bg-green-50 text-green-700 border border-green-200 px-4 py-1.5 rounded-full text-[9px] font-black uppercase italic tracking-tighter">Administrador Master Identificado</div>
                    <button onclick="exit()" class="text-red-500 font-black text-[10px] uppercase underline hover:scale-105 transition-all">Deslogar</button>
                </div>

                <div class="grid grid-cols-1 lg:grid-cols-12 gap-8">
                    <!-- Configurator -->
                    <div class="lg:col-span-5 space-y-6">
                        <div class="bg-white p-10 rounded-[3.5rem] shadow-xl border">
                            <h3 class="font-black text-slate-800 text-[10px] uppercase mb-8 border-b pb-4 flex items-center italic tracking-widest"><i class="fas fa-microscope mr-2 text-green-600"></i>Gestão de Entrada de Dados</h3>
                            
                            <input type="text" id="id_nome" placeholder="Identificação da Amostra (Ex: Anita-Época12)" class="w-full border-2 p-4 rounded-3xl mb-8 bg-slate-50 text-sm font-bold focus:border-green-600 outline-none shadow-inner">

                            <div class="flex bg-slate-100 p-1 rounded-2xl mb-8">
                                <button onclick="setTab('f')" id="tb-f" class="flex-1 py-3 text-[10px] font-black rounded-xl bg-white shadow-md text-green-700 uppercase">Arquivo CSV/XLSX</button>
                                <button onclick="setTab('m')" id="tb-m" class="flex-1 py-3 text-[10px] font-black rounded-xl text-slate-400 uppercase tracking-tighter italic">Colagem Manual</button>
                            </div>

                            <div id="ui-file"><input type="file" id="arquivo" class="block w-full border-2 border-dashed p-12 rounded-[2.5rem] bg-slate-50 text-[10px] font-bold text-slate-400 cursor-pointer"></div>

                            <div id="ui-manual" class="hidden">
                                <p class="text-[9px] font-black text-slate-400 uppercase mb-4 italic text-center underline decoration-slate-200 underline-offset-4">Área de Colagem Especial (Aceita Ctrl+V do Excel)</p>
                                <div class="bg-white rounded-2xl border overflow-hidden shadow-inner max-h-[30rem] overflow-y-auto mb-4">
                                    <table class="w-full border-collapse">
                                        <thead class="sticky top-0 shadow-sm"><tr><th class="th-lab">Data</th><th class="th-lab">Tmin</th><th class="th-lab">Tmax</th><th class="th-lab text-green-700 font-black italic italic">NF (Var.)</th></tr></thead>
                                        <tbody id="lab-grid"></tbody>
                                    </table>
                                </div>
                                <div class="flex justify-between p-2"><button onclick="addLine(5)" class="text-[9px] font-black text-green-600 uppercase hover:underline">+ 5 Linhas</button><button onclick="clearTbl()" class="text-[9px] font-black text-slate-400 italic">Limpar Grid</button></div>
                            </div>

                            <div class="bg-slate-50 p-8 rounded-[2.5rem] border text-center grid grid-cols-3 gap-4 mb-10 shadow-inner">
                                <div class="flex flex-col"><label class="text-[8px] font-bold mb-1 uppercase tracking-tighter">Faixa Mín</label><input type="number" id="tbmin" value="0.0" class="w-full border p-2 rounded-xl text-center font-bold text-xs shadow-sm"></div>
                                <div class="flex flex-col"><label class="text-[8px] font-bold mb-1 uppercase tracking-tighter">Faixa Máx</label><input type="number" id="tbmax" value="20.0" class="w-full border p-2 rounded-xl text-center font-bold text-xs shadow-sm"></div>
                                <div class="flex flex-col"><label class="text-[8px] font-black text-green-700 italic uppercase">Passo</label><input type="number" id="step" value="0.5" step="0.1" class="w-full border border-green-200 p-2 rounded-xl text-center font-bold text-xs text-green-700 bg-green-50 shadow-inner"></div>
                            </div>

                            <button onclick="calculate()" id="btnR" class="w-full bg-green-600 text-white py-5 rounded-[2rem] font-black text-xl shadow-xl hover:scale-105 transition tracking-widest uppercase">Gerar Modelagem</button>
                        </div>
                    </div>

                    <!-- Metrics Out Side -->
                    <div id="results-display" class="lg:col-span-7 hidden">
                        <div class="bg-white p-10 rounded-[3.5rem] shadow-2xl border-t-[14px] border-slate-900 sticky top-10 h-fit">
                             <div class="grid grid-cols-3 gap-6 mb-12">
                                <div class="bg-slate-50 p-6 rounded-[2rem] text-center border-b-4 border-slate-200 shadow-inner italic"><span class="text-[10px] font-black text-slate-400 block mb-2 uppercase italic tracking-widest">Temperatura Basal</span><p id="r-temp" class="text-4xl font-black font-mono text-slate-800">--</p></div>
                                <div class="bg-green-50 p-6 rounded-[2rem] text-center border-b-4 border-green-600 shadow-inner border border-green-100"><span class="text-[10px] font-black text-green-600 block mb-2 uppercase tracking-tighter italic">Coeficiente R²</span><p id="r-r2" class="text-4xl font-black font-mono text-green-600">--</p></div>
                                <div class="bg-slate-50 p-6 rounded-[2rem] text-center border-b-4 border-slate-200 shadow-inner"><span class="text-[10px] font-black text-slate-400 block mb-2 italic">Menor Erro QME</span><p id="r-qme" class="text-[12px] font-bold font-mono text-slate-500 tracking-tight">--</p></div>
                             </div>
                             
                             <div class="space-y-10">
                                <div id="chart-qme" class="h-64 border rounded-3xl bg-white p-2"></div>
                                <div id="chart-reg" class="h-64 border rounded-3xl bg-white p-2"></div>
                             </div>

                             <div id="export-lab" class="mt-10 p-10 bg-yellow-50/50 border-4 border-dotted border-yellow-200 rounded-[2.5rem] text-center">
                                <p class="text-[10px] font-black text-yellow-700 uppercase tracking-widest mb-6 italic underline decoration-yellow-400">Pacote Científico Pronto para Exportação</p>
                                <button onclick="baixarXlsx()" class="w-full bg-yellow-500 text-white font-black py-5 rounded-full text-lg shadow-xl shadow-yellow-100 hover:bg-yellow-600 transform active:scale-95 transition-all flex items-center justify-center italic tracking-widest"><i class="fas fa-file-excel mr-3 text-xl"></i>BAIXAR RELATÓRIO (.XLSX)</button>
                             </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <script>
            const S_U = "VALOR_SURL"; const S_K = "VALOR_SKEY"; const A_M = "abielgm@icloud.com";
            const _supabase = supabase.createClient(S_U, S_K);
            let uiTab = 'f'; let xlsBase64 = null;

            function clearTbl() { document.getElementById('lab-grid').innerHTML = ''; addLine(20); }
            function addLine(n) {
                for(let i=0;i<n;i++){
                    const tr = document.createElement('tr'); tr.classList.add('border-b');
                    tr.innerHTML = '<td><input type="text" class="sheet-cell c-d"></td><td><input type="text" class="sheet-cell c-min"></td><td><input type="text" class="sheet-cell c-max"></td><td><input type="text" class="sheet-cell c-nf" placeholder="..."></td>';
                    document.getElementById('lab-grid').appendChild(tr);
                }
            }
            clearTbl();

            document.addEventListener('paste', e => {
                if(e.target.classList.contains('sheet-cell')) {
                    e.preventDefault();
                    const clip = e.clipboardData.getData('text').split(/\\r?\\n/);
                    let row = e.target.closest('tr');
                    clip.forEach(t => {
                        if(!t.trim()) return;
                        const dataArr = t.split('\\t'), cells = row.querySelectorAll('input');
                        for(let i=0; i<Math.min(4, dataArr.length); i++) { cells[i].value = dataArr[i].trim().replace(',', '.'); }
                        row = row.nextElementSibling; if(!row) { addLine(1); row = document.getElementById('lab-grid').lastElementChild; }
                    });
                }
            });

            async function auth(t) {
                const em = document.getElementById('email').value, pw = document.getElementById('password').value;
                document.getElementById('loader').classList.remove('hidden');
                let r = (t === 'login') ? await _supabase.auth.signInWithPassword({email:em, password:pw}) : await _supabase.auth.signUp({email:em, password:pw});
                if(r.error) { alert("Autenticação negada: " + r.error.message); document.getElementById('loader').classList.add('hidden'); }
                else location.reload();
            }

            async function checkSession() {
                const {data:{user}} = await _supabase.auth.getUser();
                if(user) {
                    document.getElementById('login-section').classList.add('hidden');
                    document.getElementById('main-section').classList.remove('hidden');
                    document.getElementById('user-display').innerText = user.email.toLowerCase();
                    if(user.email.toLowerCase() === A_M) document.getElementById('tag-m').classList.remove('hidden');
                }
            }
            checkSession();
            async function exit() { await _supabase.auth.signOut(); localStorage.clear(); window.location.replace('/'); }
            function setTab(m) { uiTab = m; document.getElementById('tb-f').classList.toggle('bg-white', m=='f'); document.getElementById('tb-m').classList.toggle('bg-white', m=='m'); document.getElementById('ui-file').classList.toggle('hidden', m=='m'); document.getElementById('ui-manual').classList.toggle('hidden', m=='f'); }

            async function calculate() {
                document.getElementById('loader').classList.remove('hidden');
                const fd = new FormData();
                fd.append('nome_p', document.getElementById('id_nome').value || 'Amostra Científica');
                fd.append('p_min', document.getElementById('tb-min').value);
                fd.append('p_max', document.getElementById('tb-max').value);
                fd.append('p_step', document.getElementById('step').value);

                if(uiTab === 'f') {
                    const fInput = document.getElementById('arquivo');
                    if(!fInput.files[0]) { alert("Arquivo científico necessário!"); document.getElementById('loader').classList.add('hidden'); return; }
                    fd.append('file', fInput.files[0]);
                } else {
                    let dataset = [];
                    document.querySelectorAll('#lab-grid tr').forEach(tr => {
                        const vals = Array.from(tr.querySelectorAll('input')).map(i => i.value.trim());
                        if(vals[0] && vals[1] && vals[2]) {
                            if(!vals[3]) vals[3] = 'nan';
                            dataset.push(vals.join(','));
                        }
                    });
                    if(dataset.length < 5) { alert("Série histórica curta. Adicione mais dados para regressão."); document.getElementById('loader').classList.add('hidden'); return; }
                    fd.append('raw_manual', dataset.join('\\n'));
                }

                try {
                    const resp = await fetch('/v2/academic/process', {method:'POST', body:fd});
                    const d = await resp.json();
                    if(d.detail) throw new Error(d.detail);

                    xlsBase64 = d.report_xlsx; // Arquivo excel p/ download
                    document.getElementById('results-display').classList.remove('hidden');
                    document.getElementById('r-temp').innerText = d.best_val.t + "°";
                    document.getElementById('r-r2').innerText = d.best_val.r.toFixed(4);
                    document.getElementById('r-qme').innerText = d.best_val.q.toFixed(9);

                    Plotly.newPlot('chart-qme', [{x: d.charts.qx, y: d.charts.qy, mode: 'lines+markers', line:{color:'black', width:2}, marker:{color:'black'}}], {title:'Mínimo Residual (Análise Residual QME)', margin:{t:40}});
                    Plotly.newPlot('chart-reg', [{x: d.charts.rx, y: d.charts.ry, mode: 'markers', marker:{color:'gray', symbol:'circle-open'}, name:'Observado'},{x: d.charts.rx, y: d.charts.rp, mode: 'lines', line:{color:'black', dash:'dot'}, name:'Modelo'}], {title:'Regressão Final: Soma Térmica vs NF', showlegend:false, margin:{t:40}});
                    window.scrollTo({top: document.body.scrollHeight, behavior:'smooth'});
                } catch(e) {
                    alert("ALERTA INVESTIGATIVO: Verifique a coerência estatística. A Variável deve aumentar ao longo da cronologia das datas.");
                    console.error(e);
                } finally { document.getElementById('loader').classList.add('hidden'); }
            }

            function baixarXlsx() {
                if(!xlsBase64) return alert("Arquivo não gerado.");
                const bStr = atob(xlsBase64), bArr = new ArrayBuffer(bStr.length), uint8 = new Uint8Array(bArr);
                for (let i = 0; i < bStr.length; i++) uint8[i] = bStr.charCodeAt(i);
                const blob = new Blob([bArr], {type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'});
                const link = document.createElement('a');
                link.href = window.URL.createObjectURL(blob);
                link.download = `Investigacao_Tb_${new Date().getTime()}.xlsx`;
                link.click();
            }
        </script>
    </body>
    </html>
    """.replace("VALOR_SURL", SURL).replace("VALOR_SKEY", SKEY)
    return html

# =========================================================================
# ⚙️ BLOCO 4: BACKEND ENGINE (P&D - PROTEGIDO)
# =========================================================================
@app.post("/v2/academic/process")
async def handle_calculations(
    file: UploadFile = None, raw_manual: str = Form(None),
    nome_p: str = Form(""), p_min: float = Form(0.0), p_max: float = Form(20.0), p_step: float = Form(0.5)
):
    try:
        # Load logic
        if file:
            content = await file.read()
            if file.filename.endswith('.csv'):
                df = pd.read_csv(BytesIO(content), sep=None, engine='python', decimal=',')
            else:
                df = pd.read_excel(BytesIO(content))
        else:
            df = pd.read_csv(StringIO(raw_manual), names=['Data','Tmin','Tmax','NF'], header=None)

        # Standard Pre-processing
        df = fix_cols(df)
        df['Tmin'] = pd.to_numeric(df['Tmin'].astype(str).str.replace(',', '.'), errors='coerce')
        df['Tmax'] = pd.to_numeric(df['Tmax'].astype(str).str.replace(',', '.'), errors='coerce')
        df['NF'] = pd.to_numeric(df['NF'].astype(str).str.replace(',', '.'), errors='coerce')
        df['Data'] = pd.to_datetime(df['Data'], dayfirst=True, errors='coerce')
        
        # Preserve full climatology but drop corrupt weather rows
        df = df.dropna(subset=['Data', 'Tmin', 'Tmax']).sort_values('Data').reset_index(drop=True)

        # Sampling index for Phenology
        pheno_idx = df.dropna(subset=['NF']).index
        if len(pheno_idx) < 3:
            raise ValueError("Inconsistência: Verifique os nomes das colunas ou cole mais avaliações fenológicas.")

        # Computational Engine (Agrometeorology Iterative Loop)
        df['Tmed'] = (df['Tmin'] + df['Tmax']) / 2
        results_list = []
        sta_matrix = {}
        
        # Range of TB tests
        t_sequence = np.arange(p_min, p_max + p_step, p_step)

        for tb_iter in t_sequence:
            tb_iter = round(float(tb_iter), 2)
            # Biometeorological Degree Days (Clipped at Base 0)
            sta_cum = (df['Tmed'] - tb_iter).clip(lower=0).cumsum()
            
            # Sub-sampled Arrays for the Regression Step
            x_pts = sta_cum.loc[pheno_idx].values.reshape(-1, 1)
            y_pts = df.loc[pheno_idx, 'NF'].values
            
            reg_model = LinearRegression().fit(x_pts, y_pts)
            current_qme = mean_squared_error(y_pts, reg_model.predict(x_pts))
            
            results_list.append({
                'Tb': tb_iter, 
                'R2': reg_model.score(x_pts, y_pts), 
                'QME': current_qme, 
                'Ang': reg_model.coef_[0], 
                'Int': reg_model.intercept_
            })
            sta_matrix[str(tb_iter)] = sta_cum.tolist()

        # Analytics Mapping
        err_df = pd.DataFrame(results_list)
        best_row = err_df.loc[err_df['QME'].idxmin()]
        win_tb_str = str(round(best_row['Tb'], 2))

        # Synchronize plot and excel coordinates
        # We index the full weather STa list with our sampling indices
        chart_rx = [sta_matrix[win_tb_str][int(i)] for i in pheno_idx]
        chart_ry = df.loc[pheno_idx, 'NF'].tolist()
        chart_rp = [float(x * best_row['Ang'] + best_row['Int']) for x in chart_rx]

        # Construct Research Datasets for Excel
        clima_rep = df[['Data', 'Tmin', 'Tmax', 'Tmed']].copy()
        # Ensure STa columns added as per user manual style
        clima_rep['STa (Otimizada)'] = sta_matrix[win_tb_str]
        
        pheno_rep = pd.DataFrame({
            'Data': df.loc[pheno_idx, 'Data'],
            'NF (Observada)': chart_ry,
            'STa (Referencial)': chart_rx
        })

        b64_xlsx_report = gerar_xlsx_b64(clima_rep, err_df, pheno_rep, best_row['Tb'])

        return {
            "name": nome_p,
            "best_val": {"t": float(best_row['Tb']), "r": float(best_row['R2']), "q": float(best_row['QME'])},
            "charts": {
                "qx": err_df['Tb'].tolist(), "qy": err_df['QME'].tolist(),
                "rx": chart_rx, "ry": chart_ry, "rp": chart_rp
            },
            "report_xlsx": b64_xlsx_report
        }

    except Exception as e:
        import traceback
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))
