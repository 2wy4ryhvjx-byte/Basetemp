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
# 🔒 BLOCO 1: SEGURANÇA E LOGIN (NÃO MODIFICAR)
# =========================================================================
SURL = "https://iuhtopexunirguxmjiey.supabase.co"
SKEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Iml1aHRvcGV4dW5pcmd1eG1qaWV5Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzE1MjIzNTcsImV4cCI6MjA4NzA5ODM1N30.EjDui9gQ5AlRaNpoVQisGUoXmK3j74gwzq9QSguxq78"
stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "")
ADM_MAIL = "abielgm@icloud.com"

# =========================================================================
# 🧬 BLOCO 2: MOTOR CIENTÍFICO E RELATÓRIO (PROTEGIDO)
# =========================================================================
def normalize_nome(t):
    if not isinstance(t, str): return t
    return "".join(c for c in unicodedata.normalize('NFKD', t) if not unicodedata.combining(c)).lower().strip()

def converter_excel(df_periodo, qme_sheet, nf_sta_sheet, best_tb):
    """Gera o arquivo Excel completo pronto para baixar (estilo Streamlit)"""
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df_periodo.to_excel(writer, sheet_name='Dados Meteor. Periodo', index=False)
        nf_sta_sheet.to_excel(writer, sheet_name='NF e STa', index=False)
        qme_sheet.to_excel(writer, sheet_name='Análise de Erros QME', index=False)
        
        # Ajustes de formatação no Excel
        workbook  = writer.book
        date_fmt = workbook.add_format({'num_format': 'dd/mm/yyyy'})
        header_fmt = workbook.add_format({'bold': True, 'bg_color': '#E2EFDA', 'border': 1})
        
        ws1 = writer.sheets['NF e STa']
        ws1.set_column('A:A', 12, date_fmt)
        
        # Inserindo o Gráfico dentro do Excel
        chart = workbook.add_chart({'type': 'scatter', 'subtype': 'smooth'})
        chart.add_series({
            'name':       'QME vs Tb',
            'categories': ['Análise de Erros QME', 1, 0, len(qme_sheet), 0],
            'values':     ['Análise de Erros QME', 1, 2, len(qme_sheet), 2],
        })
        chart.set_title({'name': f'Temperatura Basal Ideal: {best_tb}°C'})
        writer.sheets['Análise de Erros QME'].insert_chart('E2', chart)
        
    return base64.b64encode(output.getvalue()).decode()

# =========================================================================
# 🎨 BLOCO 3: INTERFACE E EXPERIÊNCIA DO USUÁRIO
# =========================================================================
@app.get("/", response_class=HTMLResponse)
async def home_workstation():
    html_src = """
    <!DOCTYPE html>
    <html lang="pt-br">
    <head>
        <meta charset="UTF-8"><title>EstimaTB Pro - Academic Edition</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <script src="https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2"></script>
        <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
        <style>
            .spreadsheet-ui { width: 100%; border: 1px solid #e2e8f0; padding: 6px; font-size: 11px; text-align: center; outline: none; font-family: 'Courier New', monospace; }
            .spreadsheet-ui:focus { background-color: #f0fdf4; border-color: #16a34a; box-shadow: inset 0 1px 2px rgba(0,0,0,0.1); }
            .lab-header { background: #f8fafc; font-size: 9px; font-weight: 900; color: #475569; padding: 12px; border: 1px solid #e2e8f0; text-transform: uppercase; letter-spacing: 0.1em; }
        </style>
    </head>
    <body class="bg-slate-50 font-sans min-h-screen text-slate-800">
        <!-- Overlay Loading -->
        <div id="loader" class="hidden fixed inset-0 bg-white/95 z-50 flex flex-col items-center justify-center">
            <div class="animate-spin rounded-full h-16 w-16 border-t-4 border-b-4 border-green-700 mb-6"></div>
            <p class="font-black text-green-900 animate-pulse italic text-lg uppercase tracking-widest underline decoration-yellow-400">Motor de Regressão Processando...</p>
        </div>

        <div class="max-w-6xl mx-auto p-4 md:p-10">
            <!-- LOGIN SECTION -->
            <div id="login-section" class="max-w-md mx-auto bg-white p-12 rounded-[3rem] shadow-2xl mt-12 border border-slate-100 text-center animate-in fade-in duration-500">
                <h1 class="text-5xl font-black text-green-700 italic mb-1 italic tracking-tighter">EstimaTB🌿</h1>
                <p class="text-[10px] font-bold text-slate-300 uppercase tracking-[0.4em] mb-10 italic">Academic Workspace v1.0</p>
                <div class="space-y-4">
                    <input type="email" id="email" placeholder="E-mail Acadêmico" class="w-full border-2 p-4 rounded-3xl outline-none focus:border-green-600 bg-slate-50 text-sm">
                    <input type="password" id="password" placeholder="Senha" class="w-full border-2 p-4 rounded-3xl outline-none focus:border-green-600 bg-slate-50 text-sm">
                    <button onclick="handleAuth('login')" class="w-full bg-green-600 text-white py-4 rounded-3xl font-black shadow-xl hover:bg-green-700 transform active:scale-95 transition">ENTRAR NO LABORATÓRIO</button>
                    <button onclick="toggleRegMode()" id="btnSwitch" class="text-green-600 font-bold text-[10px] uppercase mt-4 block mx-auto underline tracking-widest">Criar Nova Credencial</button>
                </div>
            </div>

            <!-- DASHBOARD LAB -->
            <div id="main-section" class="hidden">
                <div class="flex flex-col md:flex-row justify-between items-center bg-white p-6 rounded-[2rem] shadow-sm border border-slate-100 mb-8 px-10 gap-6">
                    <p class="text-slate-400 font-bold text-[10px] uppercase tracking-tighter italic italic">Responsible Scientist: <span id="user-display" class="text-green-700 not-italic font-black ml-2 text-sm tracking-normal uppercase font-mono"></span></p>
                    <div id="tag-master" class="hidden bg-green-50 text-green-700 px-5 py-1.5 rounded-full font-black text-[9px] uppercase border border-green-200 shadow-sm italic">Master Investigator Activated</div>
                    <button onclick="fazerLogout()" class="bg-red-50 text-red-500 font-black text-[10px] px-6 py-2 rounded-full border border-red-100 hover:bg-red-500 hover:text-white transition uppercase tracking-widest italic underline decoration-red-200">Exit Lab</button>
                </div>

                <div class="grid grid-cols-1 lg:grid-cols-12 gap-8">
                    <!-- Configurator -->
                    <div class="lg:col-span-5 space-y-6">
                        <div class="bg-white p-10 rounded-[3rem] shadow-2xl border relative">
                            <h3 class="font-black text-slate-800 text-[10px] uppercase mb-8 border-b pb-4 flex items-center italic tracking-widest"><i class="fas fa-microscope mr-3 text-green-600"></i>Parâmetros da Investigação</h3>
                            
                            <label class="text-[9px] font-black text-slate-400 uppercase ml-2 mb-1 block">Nome do Experimento</label>
                            <input type="text" id="id_experimento" placeholder="Ex:Anita 12Época Safrinha" class="w-full border-2 p-4 rounded-3xl mb-8 text-sm font-bold bg-slate-50 focus:border-green-600 outline-none transition shadow-inner">

                            <div class="flex bg-slate-100 p-1.5 rounded-[1.5rem] mb-8 shadow-inner border border-slate-200">
                                <button onclick="tab('f')" id="bt-f" class="flex-1 py-3 text-[10px] font-black rounded-[1.1rem] bg-white shadow-md text-green-700 uppercase transition-all tracking-widest italic">Planilha Arquivo</button>
                                <button onclick="tab('m')" id="bt-m" class="flex-1 py-3 text-[10px] font-black rounded-[1.1rem] text-slate-400 uppercase transition-all tracking-tighter">Planilha Digital</button>
                            </div>

                            <div id="u-file" class="mb-10 text-center"><input type="file" id="arquivo" class="block w-full border-2 border-dashed border-slate-200 p-10 rounded-3xl bg-slate-50 text-[10px] font-bold text-slate-400 cursor-pointer"></div>

                            <div id="u-manual" class="hidden mb-10">
                                <div class="bg-white rounded-3xl border border-slate-200 overflow-hidden shadow-inner max-h-96 overflow-y-auto mb-2">
                                    <table class="w-full border-collapse">
                                        <thead><tr><th class="lab-header">Data</th><th class="lab-header">T.Min</th><th class="lab-header">T.Max</th><th class="lab-header text-green-600 italic">Variável</th></tr></thead>
                                        <tbody id="grid-lab-body"></tbody>
                                    </table>
                                </div>
                                <div class="flex justify-between items-center px-4 py-2"><button onclick="addLine(5)" class="text-[9px] font-black text-green-700 bg-green-50 px-4 py-1.5 rounded-full uppercase hover:bg-green-100 transition-all">+ Add Linhas</button><button onclick="clearLabTable()" class="text-[9px] font-black text-red-400 italic hover:text-red-600">Zerar Grid</button></div>
                            </div>

                            <div class="bg-slate-50 p-8 rounded-[2.5rem] border shadow-inner grid grid-cols-3 gap-4 mb-10 text-center relative overflow-hidden">
                                <p class="absolute top-0 right-0 p-2 text-[8px] font-black text-slate-200 uppercase pointer-events-none">Fine Tuning</p>
                                <div><label class="text-[8px] font-bold text-slate-400 mb-1 uppercase block tracking-tighter">T-Base Min</label><input type="number" id="tb-min" value="0.0" class="w-full border p-2 rounded-xl text-center font-black text-xs text-slate-600 shadow-sm outline-none"></div>
                                <div><label class="text-[8px] font-bold text-slate-400 mb-1 uppercase block tracking-tighter">T-Base Max</label><input type="number" id="tb-max" value="20.0" class="w-full border p-2 rounded-xl text-center font-black text-xs text-slate-600 shadow-sm outline-none"></div>
                                <div><label class="text-[8px] font-black text-green-700 mb-1 uppercase block tracking-tighter italic underline decoration-green-300">Intervalo</label><input type="number" id="tb-step" value="0.5" step="0.1" class="w-full border border-green-200 p-2 rounded-xl text-center font-black text-xs text-green-600 bg-green-50 shadow-inner outline-none"></div>
                            </div>

                            <button onclick="calculateAcademic()" id="runLab" class="w-full bg-green-600 text-white py-5 rounded-[2.2rem] font-black text-xl shadow-2xl shadow-green-100 hover:bg-green-700 transform hover:scale-[1.02] transition-all uppercase tracking-tighter italic">Processar Algoritmos</button>
                        </div>
                    </div>

                    <!-- Metrics Side -->
                    <div id="results-display" class="lg:col-span-7 hidden animate-in slide-in-from-right duration-700">
                        <div class="bg-white p-10 rounded-[4rem] shadow-2xl border-t-[16px] border-slate-900 sticky top-4 h-fit">
                            <h2 class="text-2xl font-black italic tracking-tighter border-b pb-4 mb-10 text-slate-800" id="study-name-out">Analytic Output Report</h2>
                             
                            <div class="grid grid-cols-3 gap-6 mb-12">
                                <div class="bg-slate-50 p-6 rounded-[2rem] text-center border-b-4 border-slate-200 shadow-inner"><p class="text-[10px] font-black text-slate-400 block mb-2 uppercase italic tracking-widest">Calculated Tb</p><p id="v-temp" class="text-4xl font-black font-mono text-slate-800">--</p></div>
                                <div class="bg-green-50/30 p-6 rounded-[2rem] text-center border-b-4 border-green-600 shadow-inner border border-green-100"><p class="text-[10px] font-black text-green-600 block mb-2 uppercase italic tracking-widest">Adjusted R²</p><p id="v-prec" class="text-4xl font-black font-mono text-green-700">--</p></div>
                                <div class="bg-slate-50 p-6 rounded-[2rem] text-center border-b-4 border-slate-200 shadow-inner"><p class="text-[10px] font-black text-slate-400 block mb-2 uppercase italic tracking-widest">Mean Err (QME)</p><p id="v-err" class="text-[12px] font-bold font-mono text-slate-600">--</p></div>
                             </div>
                             
                             <div class="space-y-10 mb-10">
                                <div id="chart-qme" class="h-64 border rounded-[2rem] shadow-sm bg-white w-full overflow-hidden p-2"></div>
                                <div id="chart-reg" class="h-64 border rounded-[2rem] shadow-sm bg-white w-full overflow-hidden p-2"></div>
                             </div>

                             <div id="export-container" class="mt-8 border-2 border-dashed border-slate-100 rounded-3xl p-6 text-center bg-slate-50">
                                <p class="text-[10px] font-black uppercase text-slate-400 mb-4 tracking-widest italic">Extração de Dados em Lote (Excel Pro Edition)</p>
                                <button onclick="downloadReport()" class="bg-yellow-500 hover:bg-yellow-600 text-white font-black px-10 py-4 rounded-full text-md shadow-xl transform active:scale-95 transition-all flex items-center mx-auto"><i class="fas fa-file-download mr-3 text-lg"></i>DOWNLOAD RELATÓRIO COMPLETO (.XLSX)</button>
                             </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <script>
            const U_EP = "U_VAL"; const K_EP = "K_VAL"; const AD_EP = "abielgm@icloud.com";
            const _lab = supabase.createClient(U_EP, K_EP);
            let activeUI = 'f'; let rMode = 'login'; let excelBlob = null;

            function clearLabTable() { document.getElementById('grid-lab-body').innerHTML = ''; addLine(20); }
            function addLine(n) {
                const b = document.getElementById('grid-lab-body');
                for(let i=0; i<n; i++) {
                    const r = document.createElement('tr');
                    r.innerHTML = '<td><input type="text" class="spreadsheet-ui in-dat"></td><td><input type="text" class="spreadsheet-ui in-tmin"></td><td><input type="text" class="spreadsheet-ui in-tmax"></td><td><input type="text" class="spreadsheet-ui in-var" placeholder="..."></td>';
                    b.appendChild(r);
                }
            }
            clearLabTable();

            // CLIPBOARD SYSTEM - Excel Mapping
            document.addEventListener('paste', e => {
                if(e.target.classList.contains('spreadsheet-ui')) {
                    e.preventDefault();
                    const raw = e.clipboardData.getData('text').split(/\\r?\\n/);
                    let row = e.target.closest('tr');
                    raw.forEach(rTxt => {
                        if(!rTxt.trim()) return;
                        const data = rTxt.split('\\t'), cells = row.querySelectorAll('input');
                        for(let i=0; i<Math.min(4, data.length); i++) { cells[i].value = data[i].trim().replace(',', '.'); }
                        row = row.nextElementSibling; if(!row) { addLine(1); row = document.getElementById('grid-lab-body').lastElementChild; }
                    });
                }
            });

            async function handleAuth(type) {
                const em = document.getElementById('email').value, ps = document.getElementById('password').value;
                document.getElementById('loader').classList.remove('hidden');
                let r = (type === 'login') ? await _lab.auth.signInWithPassword({email:em, password:ps}) : await _lab.auth.signUp({email:em, password:ps});
                if(r.error) { alert("Scientific Clearance Failed: " + r.error.message); document.getElementById('loader').classList.add('hidden'); }
                else location.reload();
            }

            async function checkS() {
                const {data:{user}} = await _lab.auth.getUser();
                if(user) {
                    document.getElementById('login-section').classList.add('hidden');
                    document.getElementById('main-section').classList.remove('hidden');
                    document.getElementById('user-display').innerText = user.email.toLowerCase();
                    if(user.email.toLowerCase() === AD_MAIL.toLowerCase()) document.getElementById('tag-master').classList.remove('hidden');
                }
            }
            checkS();
            async function fazerLogout() { await _lab.auth.signOut(); localStorage.clear(); window.location.replace('/'); }
            function tab(m) { activeUI = m; document.getElementById('bt-f').classList.toggle('bg-white', m=='f'); document.getElementById('bt-m').classList.toggle('bg-white', m=='m'); document.getElementById('u-file').classList.toggle('hidden', m=='m'); document.getElementById('u-manual').classList.toggle('hidden', m=='f'); }

            async function calculateAcademic() {
                document.getElementById('loader').classList.remove('hidden');
                const fd = new FormData();
                fd.append('e_name', document.getElementById('id_experimento').value || 'Estudo Indefinido');
                fd.append('v_min', document.getElementById('tb-min').value);
                fd.append('v_max', document.getElementById('tb-max').value);
                fd.append('v_step', document.getElementById('tb-step').value);

                if(activeUI === 'f') {
                    const f = document.getElementById('arquivo').files[0];
                    if(!f) { alert("Envie a planilha do experimento!"); document.getElementById('loader').classList.add('hidden'); return; }
                    fd.append('file', f);
                } else {
                    let d = [];
                    document.querySelectorAll('#grid-lab-body tr').forEach(tr => {
                        const inputs = Array.from(tr.querySelectorAll('input')).map(i => i.value.trim());
                        if(inputs[0] && inputs[1] && inputs[2]) { 
                            if(!inputs[3]) inputs[3] = 'nan';
                            d.push(inputs.join(',')); 
                        }
                    });
                    if(d.length < 5) { alert("Tabela Científica incompleta para regressão linear."); document.getElementById('loader').classList.add('hidden'); return; }
                    fd.append('raw', d.join('\\n'));
                }

                try {
                    const response = await fetch('/v2/scientific/analyze', {method:'POST', body:fd});
                    const d = await response.json();
                    if(d.detail) throw new Error(d.detail);

                    excelBlob = d.excel_report; // Guarda para download posterior
                    document.getElementById('results-display').classList.remove('hidden');
                    document.getElementById('v-temp').innerText = d.report.temp + "°";
                    document.getElementById('v-prec').innerText = d.report.r2.toFixed(4);
                    document.getElementById('v-err').innerText = d.report.qme.toFixed(9);
                    document.getElementById('study-name-out').innerText = "🔬 Result: " + d.name;

                    Plotly.newPlot('chart-qme', [{x:d.chart.q_x, y:d.chart.q_y, mode:'lines+markers', line:{color:'black', width:2}, marker:{color:'black'}}], {title:'Mínimo Residual (QME)', margin:{t:40}, font:{size:9}});
                    Plotly.newPlot('chart-reg', [{x:d.chart.r_x, y:d.chart.r_y, mode:'markers', marker:{color:'gray'}},{x:d.chart.r_x, y:d.chart.r_p, mode:'lines', line:{color:'black', dash:'dot'}}], {title:'Curva de Ajuste STa vs NF', showlegend:false, margin:{t:40}, font:{size:9}});
                    
                    window.scrollTo({top: 0, behavior:'smooth'});
                } catch(e) { alert("ERRO NA INVESTIGAÇÃO: " + e.message); }
                finally { document.getElementById('loader').classList.add('hidden'); }
            }

            function downloadReport() {
                if(!excelBlob) return alert("Erro na geração da planilha.");
                const bytes = atob(excelBlob);
                const ab = new ArrayBuffer(bytes.length);
                const ia = new Uint8Array(ab);
                for (let i = 0; i < bytes.length; i++) ia[i] = bytes.charCodeAt(i);
                const blob = new Blob([ab], {type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'});
                const link = document.createElement('a');
                link.href = window.URL.createObjectURL(blob);
                link.download = `Relatorio_Agrometeorologico_${new Date().getTime()}.xlsx`;
                link.click();
            }
        </script>
    </body>
    </html>
    """.replace("U_VAL", SURL).replace("K_VAL", SKEY)
    return html_src

# =========================================================================
# ⚙️ BLOCO 4: BACKEND LOGIC (CIENTIFICAMENTE VALIDADO)
# =========================================================================
@app.post("/v2/scientific/analyze")
async def run_core_algorithm(
    file: UploadFile = None, raw: str = Form(None), e_name: str = Form(""),
    v_min: float = Form(0.0), v_max: float = Form(20.0), v_step: float = Form(0.5)
):
    try:
        # Step 1: Input Processing
        if file:
            c = await file.read()
            df = pd.read_csv(BytesIO(c), sep=None, engine='python', decimal=',') if file.filename.endswith('.csv') else pd.read_excel(BytesIO(c))
        else:
            df = pd.read_csv(StringIO(raw), names=['Data','Tmin','Tmax','NF'], header=None)

        # Step 2: Hygienic Pre-processing
        # Colormap base - mapping both "Variável" and "NF" to standardized NF
        df.rename(columns=lambda c: 'NF' if normalize_nome(c) in ['nf', 'variavel'] else c, inplace=True)
        df.rename(columns=lambda c: 'Data' if normalize_nome(c) == 'data' else c, inplace=True)
        df.rename(columns=lambda c: 'Tmin' if normalize_nome(c) in ['tmin', 'tminima'] else c, inplace=True)
        df.rename(columns=lambda c: 'Tmax' if normalize_nome(c) in ['tmax', 'tmaxima'] else c, inplace=True)

        df['NF'] = pd.to_numeric(df['NF'].astype(str).str.replace(',', '.'), errors='coerce')
        df['Tmin'] = pd.to_numeric(df['Tmin'].astype(str).str.replace(',', '.'), errors='coerce')
        df['Tmax'] = pd.to_numeric(df['Tmax'].astype(str).str.replace(',', '.'), errors='coerce')
        df['Data'] = pd.to_datetime(df['Data'], dayfirst=True, errors='coerce')
        
        df = df.dropna(subset=['Data', 'Tmin', 'Tmax']).sort_values('Data')
        
        # Validation for Linear Regression (min 3 evaluations)
        pheno_rows = df.dropna(subset=['NF'])
        if len(pheno_rows) < 3:
            raise ValueError("O estudo requer ao menos 3 dias com avaliações na coluna Variável para estabelecer a correlação estatística.")

        # Step 3: Science Loop (Agrometeorological Formulas)
        df['Tmed'] = (df['Tmin'] + df['Tmax']) / 2
        p_idx = pheno_rows.index
        results = []
        sta_full_matrix = {}
        t_array = np.arange(v_min, v_max + v_step, v_step)

        for tb in t_array:
            tb = round(float(tb), 2)
            # Soma Térmica: Clipped at zero (Bio-Zero reference)
            daily_sta = (df['Tmed'] - tb).clip(lower=0).cumsum()
            
            # Sub-sample only on observed phenotypic days
            X_eval = daily_sta.loc[p_idx].values.reshape(-1, 1)
            y_eval = df.loc[p_idx, 'NF'].values
            
            lr_model = LinearRegression().fit(X_eval, y_eval)
            r2 = lr_model.score(X_eval, y_eval)
            qme = mean_squared_error(y_eval, lr_model.predict(X_eval))
            
            results.append({'Tb': tb, 'R2': r2, 'QME': qme, 'S': lr_model.coef_[0], 'I': lr_model.intercept_})
            sta_full_matrix[str(tb)] = daily_sta.tolist()

        # Step 4: Outcome Mapping
        err_df = pd.DataFrame(results)
        winner = err_df.loc[err_df['QME'].idxmin()]
        win_tb_str = str(round(winner['Tb'], 2))

        # Generate report dataframes
        df_meteor = df[['Data', 'Tmin', 'Tmax', 'Tmed']].copy()
        df_nf_sta = pd.DataFrame({
            'Data': df.loc[p_idx, 'Data'],
            'Variável (Obs.)': df.loc[p_idx, 'NF'],
            'STa (Ideal)': [float(x) for x in sta_full_matrix[win_tb_str]]
        })

        # Step 5: Professional Excel Generation (Blind to User changes)
        b64_xlsx = converter_excel(df_meteor, err_df, df_nf_sta, winner['Tb'])

        return {
            "name": e_name or "Project Anita Study",
            "report": {"temp": float(winner['Tb']), "r2": float(winner['R2']), "qme": float(winner['QME'])},
            "chart": {
                "q_x": err_df['Tb'].tolist(), "q_y": err_df['QME'].tolist(),
                "r_x": [float(x) for x in sta_full_matrix[win_tb_str]],
                "r_y": pheno_rows['NF'].astype(float).tolist(),
                "r_p": [float(x * winner['S'] + winner['I']) for x in sta_full_matrix[win_tb_str]]
            },
            "excel_report": b64_xlsx
        }
    except Exception as e:
        import traceback
        print(traceback.format_exc())
        return {"detail": str(e)}
