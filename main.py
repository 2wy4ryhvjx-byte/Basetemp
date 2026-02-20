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
# 🔒 BLOCO 1: CREDENCIAIS E LOGIN (MANTENHA ESTE BLOCO INALTERADO)
# =========================================================================
SURL = "https://iuhtopexunirguxmjiey.supabase.co"
SKEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Iml1aHRvcGV4dW5pcmd1eG1qaWV5Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzE1MjIzNTcsImV4cCI6MjA4NzA5ODM1N30.EjDui9gQ5AlRaNpoVQisGUoXmK3j74gwzq9QSguxq78"
stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "")
ADM_EMAIL = "abielgm@icloud.com"

# =========================================================================
# 🧬 BLOCO 2: PROCESSAMENTO EXCEL (xlsxwriter)
# =========================================================================
def gerar_pacote_excel(clima_df, erro_df, regressao_df, tb_calc):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        clima_df.to_excel(writer, sheet_name='Base_Meteorologica', index=False)
        regressao_df.to_excel(writer, sheet_name='Dados_da_Regressao', index=False)
        erro_df.to_excel(writer, sheet_name='Analise_QME', index=False)
        
        workbook = writer.book
        f_data = workbook.add_format({'num_format': 'dd/mm/yyyy'})
        if 'Dados_da_Regressao' in writer.sheets:
            writer.sheets['Dados_da_Regressao'].set_column('A:A', 12, f_data)
        
        # Gráfico dinâmico dentro do Excel
        chart = workbook.add_chart({'type': 'scatter', 'subtype': 'smooth'})
        chart.add_series({
            'name': 'QME vs Tb',
            'categories': ['Analise_QME', 1, 0, len(erro_df), 0],
            'values': ['Analise_QME', 1, 2, len(erro_df), 2]
        })
        chart.set_title({'name': f'Ponto Otimo de Temperatura: {tb_calc}°C'})
        writer.sheets['Analise_QME'].insert_chart('E2', chart)
        
    return base64.b64encode(output.getvalue()).decode()

# =========================================================================
# 🎨 BLOCO 3: INTERFACE E WORKSPACE
# =========================================================================
@app.get("/", response_class=HTMLResponse)
async def lab_main_page():
    html_template = """
    <!DOCTYPE html>
    <html lang="pt-br">
    <head>
        <meta charset="UTF-8"><title>EstimaTB Pro 🌿</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <script src="https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2"></script>
        <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
        <style>
            .sheet-input { width: 100%; border: none; padding: 4px; font-size: 11px; font-family: monospace; text-align: center; background: transparent; }
            .sheet-input:focus { outline: 2px solid #16a34a; background: #f0fdf4; }
            .th-lab { background: #f8fafc; font-size: 10px; font-weight: 900; color: #475569; padding: 12px; border: 1px solid #e2e8f0; text-transform: uppercase; }
        </style>
    </head>
    <body class="bg-[#F8FAFC] font-sans min-h-screen text-slate-800">
        
        <!-- Loader Sincro -->
        <div id="loader" class="hidden fixed inset-0 bg-white/95 z-50 flex flex-col items-center justify-center italic font-black text-green-700">
            <div class="animate-spin rounded-full h-16 w-16 border-t-4 border-green-600 mb-4 shadow-xl"></div>
            AGRO-MOTOR EM PROCESSAMENTO...
        </div>

        <div class="max-w-6xl mx-auto p-4 md:p-10">
            
            <!-- TELA LOGIN (VISÍVEL POR PADRÃO) -->
            <div id="login-sec" class="max-w-md mx-auto bg-white p-12 rounded-[3.5rem] shadow-2xl mt-12 border border-slate-200 text-center relative overflow-hidden">
                <div class="absolute top-0 left-0 w-full h-2 bg-yellow-400 shadow-sm"></div>
                <h1 class="text-5xl font-black text-green-700 italic mb-2 tracking-tighter uppercase decoration-yellow-400 underline decoration-4 italic">EstimaTB🌿</h1>
                <p class="text-[9px] font-bold text-slate-300 uppercase tracking-widest mb-12 italic">Academic System v1.1</p>
                <div class="space-y-4">
                    <input type="email" id="email" placeholder="E-mail" class="w-full border-2 p-4 rounded-3xl outline-none focus:border-green-600 bg-slate-50 text-sm shadow-inner">
                    <input type="password" id="password" placeholder="Senha" class="w-full border-2 p-4 rounded-3xl outline-none focus:border-green-600 bg-slate-50 text-sm shadow-inner">
                    <button onclick="logInLab()" class="w-full bg-green-600 text-white py-5 rounded-[2rem] font-black text-lg shadow-xl hover:bg-green-700 transition tracking-widest">ENTRAR NO SISTEMA</button>
                    <button onclick="toggleRegister()" id="regBtn" class="text-green-600 font-bold text-[9px] uppercase mt-4 block mx-auto underline italic tracking-tighter">Criar Registro Acadêmico</button>
                </div>
            </div>

            <!-- TELA LABORATORIO (ESCONDIDA POR PADRÃO) -->
            <div id="lab-workspace" class="hidden">
                <div class="flex flex-col md:flex-row justify-between items-center bg-white p-6 rounded-[2.5rem] border border-slate-200 mb-10 px-10 shadow-sm">
                    <p class="text-slate-400 font-bold text-[10px] uppercase italic tracking-tight italic">Authenticated Specialist: <span id="display-user" class="text-green-700 font-black not-italic text-sm"></span></p>
                    <button onclick="logOutLab()" class="text-red-500 font-black text-[10px] uppercase border px-4 py-1.5 rounded-full border-red-50 hover:bg-red-50 transition underline tracking-widest">Sair</button>
                </div>

                <div class="grid lg:grid-cols-12 gap-10">
                    <div class="lg:col-span-5 space-y-6">
                        <div class="bg-white p-10 rounded-[3.5rem] shadow-xl border relative">
                            <h3 class="font-black text-[10px] uppercase mb-10 border-b pb-4 flex items-center italic underline decoration-green-200 underline-offset-8"><i class="fas fa-database mr-3 text-green-600"></i>Painel de Modelagem</h3>
                            
                            <label class="text-[9px] font-black text-slate-400 mb-1 block uppercase italic ml-2">Identificação do Ensaio</label>
                            <input type="text" id="id_analise" placeholder="Ex: Milho Safrinha Anita" class="w-full border-2 p-4 rounded-[1.8rem] mb-10 font-bold bg-slate-50 outline-none focus:border-green-500 shadow-inner text-sm">

                            <div class="flex bg-slate-100 p-1.5 rounded-[2rem] mb-8 border border-slate-200 shadow-inner">
                                <button onclick="setTab('f')" id="btn-file" class="flex-1 py-3 text-[10px] font-black rounded-[1.6rem] bg-white shadow-md text-green-700 uppercase italic">Anexar Dataset</button>
                                <button onclick="setTab('m')" id="btn-manual" class="flex-1 py-3 text-[10px] font-black rounded-[1.6rem] text-slate-400 uppercase tracking-tighter">Inserir na Grade</button>
                            </div>

                            <div id="u-file" class="mb-10 text-center"><input type="file" id="fInput" class="block w-full border-2 border-dashed p-10 rounded-[3rem] bg-slate-50 cursor-pointer text-xs font-bold text-slate-400 shadow-inner"></div>

                            <div id="u-manual" class="hidden mb-10">
                                <p class="text-[9px] font-black text-slate-400 uppercase mb-4 italic text-center underline decoration-yellow-400">Suporte CTRL+V: Cole 4 Colunas do Excel</p>
                                <div class="rounded-3xl border border-slate-200 overflow-hidden shadow-inner bg-white mb-2 max-h-96 overflow-y-auto">
                                    <table class="w-full border-collapse">
                                        <thead class="sticky top-0 z-20"><tr><th class="th-lab">Data</th><th class="th-lab">Mín</th><th class="th-lab">Máx</th><th class="th-lab italic font-black text-green-700 uppercase">Variável</th></tr></thead>
                                        <tbody id="lab-body"></tbody>
                                    </table>
                                </div>
                                <div class="flex justify-between px-4 mt-2">
                                    <button onclick="addRow(10)" class="text-[9px] font-bold text-green-600 underline uppercase tracking-tighter hover:text-green-700 transition">+ 10 Linhas</button>
                                    <button onclick="initManualGrid()" class="text-[9px] font-bold text-red-400 uppercase italic tracking-widest">Reset</button>
                                </div>
                            </div>

                            <div class="bg-slate-50 p-8 rounded-[2.5rem] shadow-inner text-center grid grid-cols-3 gap-4 mb-10 border border-slate-100">
                                <div><label class="text-[8px] font-bold uppercase text-slate-400 block mb-2 tracking-tighter italic">Base Mín</label><input type="number" id="vmin" value="0.0" class="w-full border p-2 rounded-xl text-center font-bold text-sm shadow-sm"></div>
                                <div><label class="text-[8px] font-bold uppercase text-slate-400 block mb-2 tracking-tighter italic">Base Máx</label><input type="number" id="vmax" value="20.0" class="w-full border p-2 rounded-xl text-center font-bold text-sm shadow-sm"></div>
                                <div><label class="text-[8px] font-black text-green-700 italic block mb-2 uppercase tracking-tighter italic">Ref Passo</label><input type="number" id="vstep" value="0.5" step="0.1" class="w-full border border-green-200 bg-white p-2 rounded-xl text-center font-black text-green-700 text-sm shadow-inner focus:ring-1 focus:ring-green-400"></div>
                            </div>

                            <button onclick="gerarCalculo()" class="w-full bg-green-600 text-white py-6 rounded-[2.5rem] font-black text-xl shadow-2xl shadow-green-100 hover:bg-green-700 transform active:scale-95 transition-all tracking-widest uppercase italic italic underline decoration-yellow-400 decoration-2">Executar Modelagem</button>
                        </div>
                    </div>

                    <div id="res-side" class="lg:col-span-7 hidden animate-in slide-in-from-right duration-500">
                        <div class="bg-white p-10 rounded-[3.5rem] shadow-2xl border-t-[14px] border-slate-900 sticky top-10 h-fit border-b">
                             <div class="grid grid-cols-3 gap-6 mb-12 text-center">
                                <div class="bg-slate-50 p-6 rounded-[2.2rem] border shadow-inner italic border-slate-200"><p class="text-[9px] font-black text-slate-400 uppercase mb-2">Tb Resultante</p><p id="o-temp" class="text-4xl font-black font-mono tracking-tighter text-slate-800">--</p></div>
                                <div class="bg-green-50 p-6 rounded-[2.2rem] border-2 border-green-100 shadow-inner"><p class="text-[10px] font-black text-green-600 mb-2 uppercase tracking-widest">Precisão (R²)</p><p id="o-r2" class="text-4xl font-black font-mono text-green-600 tracking-tight">--</p></div>
                                <div class="bg-slate-50 p-6 rounded-[2.2rem] border shadow-inner border-slate-200"><p class="text-[9px] font-bold text-slate-300 italic uppercase mb-2">Min Erro QME</p><p id="o-qme" class="text-[14px] font-black font-mono text-slate-400">--</p></div>
                             </div>
                             
                             <div class="space-y-10 mb-10">
                                <div id="gr1" class="h-64 border rounded-[2.5rem] p-3 bg-white shadow-inner overflow-hidden"></div>
                                <div id="gr2" class="h-64 border rounded-[2.5rem] p-3 bg-white shadow-inner overflow-hidden"></div>
                             </div>

                             <div class="rounded-[2rem] border border-slate-200 mb-8 overflow-hidden bg-slate-50">
                                <h4 class="p-3 text-[10px] font-black uppercase text-slate-500 italic ml-4 flex justify-between mr-6 items-center">
                                    <span>Dataset Processado e Higienizado</span>
                                    <i class="fas fa-check-circle text-green-500"></i>
                                </h4>
                                <div id="v-prev" class="max-h-56 overflow-auto bg-white border-t border-slate-100 text-[10px] font-mono leading-relaxed"></div>
                             </div>

                             <div id="btn-final-export" class="p-10 bg-amber-50 rounded-[3rem] border border-amber-200 border-dotted text-center shadow-inner hover:bg-amber-100/30 transition-all duration-300">
                                <p class="text-[10px] font-black uppercase text-amber-700 italic tracking-[0.2em] mb-6 decoration-yellow-400 underline underline-offset-4">Geração de Laudo Agrometeorológico Pro</p>
                                <button onclick="saveExcel()" class="w-full bg-yellow-500 hover:bg-yellow-600 text-white font-black py-6 rounded-full text-lg shadow-xl shadow-yellow-100 flex items-center justify-center transition-all transform active:scale-95 italic uppercase"><i class="fas fa-file-export mr-4 text-2xl"></i>BAIXAR RELATÓRIO (.XLSX)</button>
                             </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <script>
            const SV_U = "EP_URL_SET"; const SV_K = "EP_KEY_SET"; const MY_M = "abielgm@icloud.com";
            const _lab = supabase.createClient(SV_U, SV_K);
            let uiM = 'f'; let xls64_raw = null;

            // GERENCIAMENTO DA GRADE
            function initManualGrid() { document.getElementById('lab-body').innerHTML = ''; addRow(20); }
            function addRow(n) {
                const b = document.getElementById('lab-body');
                for(let i=0; i<n; i++) {
                    const r = document.createElement('tr'); r.className = 'border-b border-slate-100 hover:bg-slate-50 transition';
                    r.innerHTML = '<td><input type="text" class="sheet-input c-d"></td><td><input type="text" class="sheet-input c-mi"></td><td><input type="text" class="sheet-input c-ma"></td><td><input type="text" class="sheet-input c-v" placeholder="..."></td>';
                    b.appendChild(r);
                }
            }
            initManualGrid();

            // SUPORTE AO COPIAR DO EXCEL - Lógica restaurada para precisão 4 colunas
            document.addEventListener('paste', e => {
                if(e.target.classList.contains('sheet-input')) {
                    e.preventDefault();
                    const clip_t = e.clipboardData.getData('text');
                    const clip_r = clip_t.split(/\\r?\\n/);
                    let focusRow = e.target.closest('tr');
                    
                    clip_r.forEach(linhaTxt => {
                        if(linhaTxt.trim() === '') return;
                        const dCol = linhaTxt.split('\\t'), cellIns = focusRow.querySelectorAll('input');
                        for(let i=0; i<Math.min(4, dCol.length, cellIns.length); i++){
                            cellIns[i].value = dCol[i].trim().replace(',', '.'); 
                        }
                        focusRow = focusRow.nextElementSibling; if(!focusRow){ addRow(1); focusRow = document.getElementById('lab-body').lastElementChild; }
                    });
                }
            });

            async function logInLab() {
                const em = document.getElementById('email').value, pw = document.getElementById('password').value;
                document.getElementById('loader').classList.remove('hidden');
                let {data, error} = await _lab.auth.signInWithPassword({email:em, password:pw});
                if(error){ 
                    alert("Acesso Negado: Identificação incorreta no sistema.\\n(" + error.message + ")"); 
                    document.getElementById('loader').classList.add('hidden'); 
                } else {
                    location.reload();
                }
            }

            // RECUPERAÇÃO DE LOGICÁ ESTÁVEL: Session Manager
            async function sessionControl() {
                const {data:{user}} = await _lab.auth.getUser();
                if(user) {
                    document.getElementById('login-sec').classList.add('hidden');
                    document.getElementById('lab-workspace').classList.remove('hidden');
                    document.getElementById('display-user').innerText = user.email.toLowerCase();
                } else {
                    document.getElementById('login-sec').classList.remove('hidden');
                    document.getElementById('lab-workspace').classList.add('hidden');
                }
            }
            sessionControl();

            async function logOutLab() { 
                await _lab.auth.signOut(); localStorage.clear(); sessionStorage.clear(); window.location.replace('/'); 
            }
            
            function setTab(m) { 
                uiM = m; 
                document.getElementById('btn-file').classList.toggle('bg-white', m=='f'); document.getElementById('btn-manual').classList.toggle('bg-white', m=='m'); 
                document.getElementById('u-file').classList.toggle('hidden', m=='m'); document.getElementById('u-manual').classList.toggle('hidden', m=='f'); 
            }

            async function gerarCalculo() {
                document.getElementById('loader').classList.remove('hidden');
                const fd = new FormData();
                fd.append('label_agro', document.getElementById('id_analise').value || 'Projeto Experimental EstimaTB');
                fd.append('vmin_a', document.getElementById('vmin').value);
                fd.append('vmax_a', document.getElementById('vmax').value);
                fd.append('vstep_a', document.getElementById('vstep').value);

                if(uiM === 'f') {
                    const fObj = document.getElementById('fInput');
                    if(!fObj.files[0]){ alert("Erro: Envie o dataset do laboratório."); document.getElementById('loader').classList.add('hidden'); return; }
                    fd.append('file', fObj.files[0]);
                } else {
                    let dArr = [];
                    document.querySelectorAll('#lab-body tr').forEach(tr => {
                        const vals = Array.from(tr.querySelectorAll('input')).map(i => i.value.trim().replace(',', '.'));
                        if(vals[0] && vals[1] && vals[2]) { if(!vals[3]) vals[3] = 'nan'; dArr.push(vals.join(';')); }
                    });
                    if(dArr.length < 3) { alert("Base manual insuficiente."); document.getElementById('loader').classList.add('hidden'); return; }
                    fd.append('manual_dataset', dArr.join('\\n'));
                }

                try {
                    const resp = await fetch('/vfinal/lab/calculate', {method:'POST', body:fd});
                    const d = await resp.json();
                    if(d.detail) throw new Error(d.detail);

                    xls64_raw = d.xls_file;
                    document.getElementById('res-side').classList.remove('hidden');
                    document.getElementById('o-temp').innerText = d.best_v.t + "°";
                    document.getElementById('o-r2').innerText = d.best_v.r.toFixed(4);
                    document.getElementById('o-qme').innerText = d.best_v.q.toFixed(9);

                    // P&B Cientifico
                    Plotly.newPlot('gr1', [{x: d.plt.qx, y: d.plt.qy, mode: 'lines+markers', line:{color:'black'}, marker:{color:'black'}}], {title:'Analítico QME', font:{size:10}});
                    Plotly.newPlot('gr2', [{x: d.plt.rx, y: d.plt.ry, mode:'markers', marker:{color:'gray', symbol:'circle-open'}, name:'Obs.'},{x: d.plt.rx, y: d.plt.rp, mode:'lines', line:{color:'black', dash:'dot'}}], {title:'Regressão: NF vs STa', font:{size:10}, showlegend:false});

                    let tH = '<table class="w-full text-left font-mono text-[9px] border-collapse"><thead class="bg-slate-50 sticky top-0 z-10 border-b"><tr><th class="p-2 border-r uppercase">Time</th><th class="p-2 border-r text-center">TMin</th><th class="p-2 border-r text-center">TMax</th><th class="p-2 text-center text-green-700 italic">Var (NF)</th></tr></thead><tbody>';
                    d.preview_tbl.forEach(row_i => { 
                        tH += `<tr class="border-b"><td class="p-2 border-r uppercase text-slate-500">${row_i.Data}</td><td class="p-2 border-r text-center font-bold">${row_i.Tmin}</td><td class="p-2 border-r text-center font-bold">${row_i.Tmax}</td><td class="p-2 text-center text-green-700 font-bold">${row_i.NF}</td></tr>`; 
                    });
                    document.getElementById('v-prev').innerHTML = tH + '</tbody></table>';

                    window.scrollTo({top: document.body.scrollHeight, behavior:'smooth'});
                } catch(e) {
                    alert("PROCESS_ERROR: Falha de regressão científica.\\n" + e.message);
                } finally { document.getElementById('loader').classList.add('hidden'); }
            }

            function saveExcel() {
                if(!xls64_raw) return alert("Planilha não processada.");
                const bs = atob(xls64_raw), ab = new ArrayBuffer(bs.length), u8 = new Uint8Array(ab);
                for(let i=0; i<bs.length; i++) u8[i] = bs.charCodeAt(i);
                const bL = new Blob([ab], {type:'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'});
                const linkObj = document.createElement('a'); linkObj.href = window.URL.createObjectURL(bL);
                linkObj.download = `EstimaTB_Resultado_Exp.xlsx`; linkObj.click();
            }
        </script>
        <style>.sheet-input { width: 100%; border:none; outline:none; text-align:center; padding: 6px; font-family:monospace; }</style>
    </body>
    </html>
    """.replace("EP_URL_SET", SURL).replace("EP_KEY_SET", SKEY)
    return html_template

# =========================================================================
# ⚙️ BLOCO 4: BACKEND FINAL ENGINE (PROTEGIDO CONTRA ERROS DE TIPO)
# =========================================================================
@app.post("/vfinal/lab/calculate")
async def laboratory_calculation(
    file: UploadFile = None, manual_dataset: str = Form(None), label_agro: str = Form(""),
    vmin_a: float = Form(0.0), vmax_a: float = Form(20.0), vstep_a: float = Form(0.5)
):
    try:
        # Load Dataset
        if file:
            c = await file.read()
            df = pd.read_csv(BytesIO(c), sep=None, engine='python', decimal=',') if file.filename.endswith('.csv') else pd.read_excel(BytesIO(c))
        else:
            # Separador ponto-e-virgula protege contra decimais br (vírgula)
            df = pd.read_csv(StringIO(manual_dataset), sep=';', names=['Data','Tmin','Tmax','NF'], header=None)

        # Standard Normalization (Renomeia Data, Tmin, Tmax, NF)
        def clean_sc_cols(x):
            nx = "".join(c for c in unicodedata.normalize('NFKD', str(x)) if not unicodedata.combining(c)).lower().strip()
            if nx == 'data': return 'Data'
            if nx in ['tmin','tminima','tmín']: return 'Tmin'
            if nx in ['tmax','tmaxima','tmáx']: return 'Tmax'
            if nx in ['nf','variavel','variável']: return 'NF'
            return x
        df.rename(columns=clean_sc_cols, inplace=True)

        for col_name in ['Tmin','Tmax','NF']:
            if col_name in df.columns:
                df[col_name] = pd.to_numeric(df[col_name].astype(str).str.replace(',', '.').str.replace('[^0-9\\.\\-]', '', regex=True), errors='coerce')
        
        df['Data'] = pd.to_datetime(df['Data'], dayfirst=True, errors='coerce')
        df = df.dropna(subset=['Data','Tmin','Tmax']).sort_values('Data').reset_index(drop=True)

        points_pheno = df.dropna(subset=['NF'])
        if len(points_pheno) < 3:
            raise ValueError(f"Foram encontradas apenas {len(points_pheno)} observações fenomenológicas. O sistema acadêmico exige o mínimo de 3 dias de campo para realizar a modelagem linear.")

        # Logic Matrix
        df['Tmed'] = (df['Tmin'] + df['Tmax']) / 2
        p_idx = points_pheno.index
        results_track = []
        winner_data = {}
        abs_min_qme = float('inf')

        scan_t_range = np.arange(vmin_a, vmax_a + vstep_a, vstep_a)
        for tb_i in scan_t_range:
            tb_i = round(float(tb_i), 2)
            sta_acumulado = (df['Tmed'] - tb_i).clip(lower=0).cumsum()
            
            # Sincronia de Amostragem (Garante Array Matching)
            X_model = sta_acumulado.loc[p_idx].values.reshape(-1, 1)
            y_model = df.loc[p_idx, 'NF'].values
            
            reg_f = LinearRegression().fit(X_model, y_model)
            qme_s = mean_squared_error(y_model, reg_f.predict(X_model))
            r2_s = reg_f.score(X_model, y_model)
            results_track.append({'Tb': tb_i, 'R2': r2_s, 'QME': qme_s})
            
            if qme_s < abs_min_qme:
                abs_min_qme = qme_s
                winner_data = {
                    't': tb_i, 'r2': r2_s, 'qme': qme_s, 'a': reg_f.coef_[0], 'b': reg_f.intercept_,
                    'plt_x': sta_acumulado.loc[p_idx].tolist(),
                    'full_sta': sta_acumulado.tolist()
                }

        log_err_df = pd.DataFrame(results_track)
        
        # Datasets para Excel (Otimizado)
        final_clima = df[['Data','Tmin','Tmax','Tmed']].copy()
        final_clima['STa_Optimized'] = winner_data['full_sta']
        
        final_reg = pd.DataFrame({
            'Data': df.loc[p_idx, 'Data'],
            'Medicao_Variavel_NF': df.loc[p_idx, 'NF'],
            'STa_Acumulado_Ideal': winner_data['plt_x']
        })

        xlsx_64 = gerar_pacote_excel(final_clima, log_err_df, final_reg, winner_data['t'])

        return {
            "label_i": label_agro or "Project Data Analysis",
            "best_v": {"t": float(winner_data['t']), "r": float(winner_data['r2']), "q": float(winner_data['qme'])},
            "plt": {
                "qx": log_err_df['Tb'].tolist(), "qy": log_err_df['QME'].tolist(),
                "rx": [float(v) for v in winner_data['plt_x']], 
                "ry": points_pheno['NF'].astype(float).tolist(),
                "rp": [float(x_i * winner_data['a'] + winner_data['b']) for x_i in winner_data['plt_x']]
            },
            "preview_tbl": df.head(50).astype(str).to_dict(orient="records"),
            "xls_file": xlsx_64
        }
    except Exception as e:
        import traceback
        print(traceback.format_exc())
        return {"detail": str(e)}
