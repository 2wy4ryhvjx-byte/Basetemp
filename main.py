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
# 🔒 BLOCO 1: LOGIN E SEGURANÇA (ESTÁVEL)
# =========================================================================
SURL = "https://iuhtopexunirguxmjiey.supabase.co"
SKEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Iml1aHRvcGV4dW5pcmd1eG1qaWV5Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzE1MjIzNTcsImV4cCI6MjA4NzA5ODM1N30.EjDui9gQ5AlRaNpoVQisGUoXmK3j74gwzq9QSguxq78"
stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "")
ADM_MAIL = "abielgm@icloud.com"

# =========================================================================
# 🧬 BLOCO 2: LOGICA DE RELATÓRIOS EXCEL (PROTEGIDO)
# =========================================================================
def build_xls_file(clima, erros, regressao, tb):
    out = BytesIO()
    with pd.ExcelWriter(out, engine='xlsxwriter') as writer:
        clima.to_excel(writer, sheet_name='Base_Meteorologica', index=False)
        regressao.to_excel(writer, sheet_name='Regressao_NF_STa', index=False)
        erros.to_excel(writer, sheet_name='Tabela_QME', index=False)
        wb = writer.book
        dt_f = wb.add_format({'num_format': 'dd/mm/yyyy'})
        if 'Regressao_NF_vs_STa' in writer.sheets:
            writer.sheets['Regressao_NF_vs_STa'].set_column('A:A', 12, dt_f)
    return base64.b64encode(out.getvalue()).decode()

# =========================================================================
# 🎨 BLOCO 3: INTERFACE PROFISSIONAL
# =========================================================================
@app.get("/", response_class=HTMLResponse)
async def lab_ui():
    html_src = """
    <!DOCTYPE html>
    <html lang="pt-br">
    <head>
        <meta charset="UTF-8"><title>EstimaTB Pro 🌿</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <script src="https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2"></script>
        <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
        <style>
            .sheet-input { width: 100%; border: none; padding: 4px; font-size: 11px; text-align: center; outline: none; background: transparent; }
            .sheet-input:focus { background: #f0fdf4; border-bottom: 2px solid #16a34a; }
            .th-agro { background: #f8fafc; font-size: 9px; font-weight: 900; color: #64748b; padding: 10px; border: 1px solid #e2e8f0; text-transform: uppercase; }
        </style>
    </head>
    <body class="bg-[#F9FAFB] font-sans min-h-screen text-slate-800">
        <div id="loader" class="hidden fixed inset-0 bg-white/95 z-50 flex flex-col items-center justify-center font-black text-green-700 italic">
            <div class="animate-spin rounded-full h-16 w-16 border-t-4 border-b-4 border-green-600 mb-4"></div>
            ESTATÍSTICA EM PROCESSAMENTO...
        </div>

        <div class="max-w-6xl mx-auto p-4 md:p-8">
            <!-- LOGIN -->
            <div id="login-sec" class="max-w-md mx-auto bg-white p-12 rounded-[3rem] shadow-2xl mt-12 border text-center">
                <h1 class="text-4xl font-black text-green-700 mb-2 italic tracking-tighter uppercase decoration-yellow-400 underline decoration-4 italic">EstimaTB🌿</h1>
                <p class="text-[9px] font-bold text-slate-300 uppercase tracking-widest mb-10">Agro-Intelligence v2.0</p>
                <div class="space-y-4">
                    <input type="email" id="email" placeholder="E-mail Acadêmico" class="w-full border-2 p-4 rounded-3xl mb-2 focus:border-green-600 outline-none bg-slate-50 text-sm">
                    <input type="password" id="password" placeholder="Senha" class="w-full border-2 p-4 rounded-3xl mb-8 focus:border-green-600 outline-none bg-slate-50 text-sm">
                    <button onclick="entrar()" class="w-full bg-green-600 text-white py-5 rounded-3xl font-black shadow-xl hover:bg-green-700">ENTRAR NO SISTEMA</button>
                    <button onclick="toggleCad()" id="btn-sw" class="text-green-600 font-bold text-[9px] uppercase mt-6 block mx-auto tracking-widest">Criar Cadastro</button>
                </div>
            </div>

            <!-- LAB DASHBOARD -->
            <div id="lab-sec" class="hidden animate-in fade-in duration-500">
                <div class="flex flex-col md:flex-row justify-between items-center bg-white p-5 rounded-[2rem] border border-slate-200 mb-6 px-10 shadow-sm">
                    <p class="font-bold text-[10px] uppercase text-slate-400 italic">Pesquisador Logado: <span id="u-display" class="text-green-700 font-black not-italic text-sm"></span></p>
                    <button onclick="sair()" class="text-red-500 font-black text-[10px] uppercase border px-4 py-1 rounded-full border-red-50">Logoff</button>
                </div>

                <div class="grid lg:grid-cols-12 gap-8">
                    <!-- Painel Entrada -->
                    <div class="lg:col-span-5 space-y-6">
                        <div class="bg-white p-8 rounded-[3.5rem] shadow-xl border">
                            <h3 class="font-black text-[10px] uppercase mb-10 border-b pb-4 flex items-center italic tracking-widest text-slate-500 underline decoration-green-200"><i class="fas fa-file-invoice mr-3 text-green-600"></i>Gestão Analítica de Dados</h3>
                            
                            <label class="text-[9px] font-black text-slate-400 ml-2 block mb-1">Nome do Ensaio / Amostra</label>
                            <input type="text" id="a_id" placeholder="Ex: Milho Anita 2025" class="w-full border-2 p-4 rounded-3xl mb-8 font-bold bg-slate-50 focus:border-green-500 outline-none text-sm shadow-inner">

                            <div class="flex bg-slate-100 p-1 rounded-2xl mb-8 shadow-inner border border-slate-200">
                                <button onclick="tab('f')" id="b-f" class="flex-1 py-3 text-[10px] font-black rounded-xl bg-white shadow-md text-green-700 uppercase italic">Importar Planilha</button>
                                <button onclick="tab('m')" id="b-m" class="flex-1 py-3 text-[10px] font-black rounded-xl text-slate-400 uppercase tracking-tighter transition-all">Digitação Direta</button>
                            </div>

                            <div id="u-file"><input type="file" id="fInput" class="block w-full border-2 border-dashed p-10 rounded-[2.5rem] bg-slate-50 text-[10px] italic"></div>

                            <div id="u-manual" class="hidden mb-6">
                                <p class="text-[9px] font-bold text-slate-400 uppercase mb-4 italic text-center underline decoration-slate-100">Área de Colagem (Suporte total Excel CTRL+V)</p>
                                <div class="rounded-3xl border border-slate-200 overflow-hidden shadow-inner bg-white mb-2 max-h-96 overflow-y-auto">
                                    <table class="w-full border-collapse">
                                        <thead class="sticky top-0 z-20"><tr><th class="agro-th">Data</th><th class="agro-th">Min</th><th class="agro-th">Max</th><th class="agro-th italic text-green-700 font-bold uppercase">NF</th></tr></thead>
                                        <tbody id="agro-body"></tbody>
                                    </table>
                                </div>
                                <div class="flex justify-between p-2"><button onclick="addLine(5)" class="text-[9px] font-black text-green-600 uppercase underline">+ Adicionar</button><button onclick="limpa()" class="text-[9px] font-bold text-red-300 italic uppercase">Limpar</button></div>
                            </div>

                            <div class="bg-slate-50 p-6 rounded-3xl text-center grid grid-cols-3 gap-3 mb-10 border border-slate-100 shadow-inner">
                                <div class="flex flex-col"><label class="text-[8px] font-black uppercase text-slate-400">Tb Início</label><input type="number" id="tb-min" value="0.0" class="w-full border p-2 rounded-xl text-center font-bold"></div>
                                <div class="flex flex-col"><label class="text-[8px] font-black uppercase text-slate-400">Tb Final</label><input type="number" id="tb-max" value="20.0" class="w-full border p-2 rounded-xl text-center font-bold"></div>
                                <div class="flex flex-col"><label class="text-[8px] font-bold uppercase text-green-700 italic">Passo</label><input type="number" id="tb-step" value="0.5" step="0.1" class="w-full border-2 border-green-200 bg-white p-2 rounded-xl text-center font-bold text-green-700 shadow-sm"></div>
                            </div>

                            <button onclick="calcularTb()" id="runBtn" class="w-full bg-green-600 text-white py-6 rounded-[2.2rem] font-black text-2xl shadow-xl shadow-green-100 hover:scale-[1.02] transition uppercase italic underline decoration-yellow-300">EXECUTAR MODELAGEM</button>
                        </div>
                    </div>

                    <!-- Side Res -->
                    <div id="out-view" class="lg:col-span-7 hidden animate-in slide-in-from-right duration-500">
                        <div class="bg-white p-10 rounded-[4rem] shadow-2xl border-t-[14px] border-slate-900 sticky top-4 h-fit border-slate-200">
                            <h2 class="text-xl font-black italic border-b pb-6 mb-10" id="study-label-final">Scientific Analytic Summary</h2>
                             <div class="grid grid-cols-3 gap-6 mb-12 text-center">
                                <div class="bg-slate-50 p-6 rounded-[2.2rem] border shadow-inner italic"><p class="text-[9px] font-black text-slate-300 uppercase">Temperatura Basal</p><p id="v-tb" class="text-4xl font-black font-mono tracking-tighter">--</p></div>
                                <div class="bg-green-50 p-6 rounded-[2.2rem] border-2 border-green-100 shadow-inner"><p class="text-[10px] font-black text-green-600 uppercase italic">Ajuste R²</p><p id="v-r2" class="text-4xl font-black font-mono text-green-600 tracking-tight">--</p></div>
                                <div class="bg-slate-50 p-6 rounded-[2.2rem] border shadow-inner"><p class="text-[9px] font-bold text-slate-300 italic uppercase">Min QME</p><p id="v-qme" class="text-[12px] font-black font-mono text-slate-400 tracking-tighter">--</p></div>
                             </div>
                             
                             <div class="space-y-6 mb-12">
                                <div id="gr1" class="h-64 border rounded-[2.5rem] bg-white p-4 shadow-inner overflow-hidden"></div>
                                <div id="gr2" class="h-64 border rounded-[2.5rem] bg-white p-4 shadow-inner overflow-hidden"></div>
                             </div>

                             <div class="border border-slate-200 rounded-[2.5rem] overflow-hidden bg-slate-50 mb-10">
                                <p class="bg-slate-100 p-4 text-[9px] font-black uppercase text-slate-400 italic flex justify-between mr-6 items-center italic underline">Data Tracking Visualizer (Previsualização)<i class="fas fa-search"></i></p>
                                <div id="sanit-preview" class="max-h-56 overflow-auto bg-white border-t p-1"></div>
                             </div>

                             <div class="p-8 bg-amber-50 rounded-[3rem] border-2 border-amber-200 border-dotted text-center shadow-inner hover:bg-amber-100/30 transition-all duration-300">
                                <button onclick="baixarDoc()" class="w-full bg-yellow-500 hover:bg-yellow-600 text-white font-black py-5 px-12 rounded-full text-md shadow-xl flex items-center justify-center mx-auto tracking-widest uppercase italic transform active:scale-95"><i class="fas fa-file-excel mr-4 text-3xl"></i>Exportar Relatório Acadêmico (.XLSX)</button>
                             </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <script>
            const SU = "URL_VAL"; const SK = "KEY_VAL"; const ME = "abielgm@icloud.com";
            const _sb = supabase.createClient(SU, SK);
            let uiM = 'f'; let b64File = null;

            function limpa() { document.getElementById('agro-body').innerHTML = ''; addLine(15); }
            function addLine(n) {
                const b = document.getElementById('agro-body');
                for(let i=0; i<n; i++){
                    const tr = document.createElement('tr'); tr.className='border-b hover:bg-slate-50 transition';
                    tr.innerHTML = '<td><input type="text" class="sheet-input c-dat"></td><td><input type="text" class="sheet-input c-mi"></td><td><input type="text" class="sheet-input c-ma"></td><td><input type="text" class="sheet-input c-nf" placeholder="..."></td>';
                    b.appendChild(tr);
                }
            }
            addLine(25);

            // LOGICA COLAR BRUTAL: Limpa aspas e lixo do Excel
            document.addEventListener('paste', e => {
                if(e.target.classList.contains('sheet-input')) {
                    e.preventDefault();
                    const text = e.clipboardData.getData('text').trim();
                    const rowsArr = text.split(/\\r?\\n/);
                    let targetRow = e.target.closest('tr');
                    
                    rowsArr.forEach(txtRow => {
                        if(!txtRow.trim()) return;
                        const cellsArr = txtRow.split('\\t'), inps = targetRow.querySelectorAll('input');
                        for(let i=0; i<Math.min(4, cellsArr.length, inps.length); i++){
                            // Normalização: troca vírgula decimal do Excel BR por ponto no ato da colagem
                            inps[i].value = cellsArr[i].trim().replace(',', '.');
                        }
                        targetRow = targetRow.nextElementSibling; if(!targetRow){ addLine(1); targetRow = document.getElementById('agro-body').lastElementChild; }
                    });
                }
            });

            async function entrar() {
                const em = document.getElementById('email').value, pw = document.getElementById('password').value;
                document.getElementById('loader').classList.remove('hidden');
                let {data, error} = await _sb.auth.signInWithPassword({email:em, password:pw});
                if(error) { alert("Scientific Clear: Credenciais negadas."); document.getElementById('loader').classList.add('hidden'); }
                else location.reload();
            }

            async function checkSession() {
                const {data:{user}} = await _sb.auth.getUser();
                if(user) {
                    document.getElementById('login-sec').classList.add('hidden');
                    document.getElementById('lab-sec').classList.remove('hidden');
                    document.getElementById('u-display').innerText = user.email.toLowerCase();
                }
            }
            checkSession();
            async function sair() { await _sb.auth.signOut(); localStorage.clear(); window.location.replace('/'); }
            function tab(m) { uiM = m; document.getElementById('btn-f').classList.toggle('bg-white', m=='f'); document.getElementById('btn-m').classList.toggle('bg-white', m=='m'); document.getElementById('u-file').classList.toggle('hidden', m=='m'); document.getElementById('u-manual').classList.toggle('hidden', m=='f'); }

            async function calcularTb() {
                document.getElementById('loader').classList.remove('hidden');
                const form_d = new FormData();
                form_d.append('label', document.getElementById('a_id').value || 'Investigation Project');
                form_d.append('vmin_a', document.getElementById('tb-min').value);
                form_d.append('vmax_a', document.getElementById('tb-max').value);
                form_d.append('vstep_a', document.getElementById('tb-step').value);

                if(uiM === 'f') {
                    const fi_obj = document.getElementById('fInput');
                    if(!fi_obj.files[0]){ alert("Nenhuma amostra climática detectada."); document.getElementById('loader').classList.add('hidden'); return; }
                    form_d.append('file', fi_obj.files[0]);
                } else {
                    let dOutStrings = [];
                    document.querySelectorAll('#agro-body tr').forEach(tr_node => {
                        // Enviamos usando um separador único PIPE | que não choca com nada
                        const inputsValues = Array.from(tr_node.querySelectorAll('input')).map(input_node => input_node.value.trim().replace(',', '.'));
                        // Só adicionamos a linha se DATA e TMIN existirem (limpa lixo)
                        if(inputsValues[0] && inputsValues[1] && inputsValues[2]) {
                            if(!inputsValues[3]) inputsValues[3] = 'nan'; dOutStrings.push(inputsValues.join('|'));
                        }
                    });
                    if(dOutStrings.length < 5) { alert("Massa de dados insuficiente para regressão de erro."); document.getElementById('loader').classList.add('hidden'); return; }
                    form_d.append('dataset_manual', dOutStrings.join('\\n'));
                }

                try {
                    const response_serv = await fetch('/api/agro/calculate/pro', {method:'POST', body:form_d});
                    const d_j = await response_serv.json();
                    if(d_j.detail) throw new Error(d_j.detail);

                    b64File = d_j.xlsx_64;
                    document.getElementById('out-view').classList.remove('hidden');
                    document.getElementById('v-tb').innerText = d_j.output.tb_opt + "°";
                    document.getElementById('v-r2').innerText = d_j.output.r2_opt.toFixed(4);
                    document.getElementById('v-qme').innerText = d_j.output.qme_opt.toFixed(9);
                    document.getElementById('study-label-final').innerText = "🔬 Result Index: " + d_j.identificacao;

                    Plotly.newPlot('gr1', [{x: d_j.charts.qx, y: d_j.charts.qy, mode: 'lines+markers', line:{color:'black'}, marker:{size:4}}], {title:'Mínimo Residual (Estatística QME)', font:{size:10}, margin:{t:40}});
                    Plotly.newPlot('gr2', [{x: d_j.charts.rx, y: d_j.charts.ry, mode:'markers', marker:{color:'gray', symbol:'circle-open'}, name:'Obs.'},{x: d_j.charts.rx, y: d_j.charts.rp, mode:'lines', line:{color:'black', dash:'dot'}, name:'Reg'}], {title:'Regressão Final: NF vs Soma Térmica', font:{size:10}, showlegend:false, margin:{t:40}});

                    // Data Previs Tabular
                    let prevTabH = '<table class="w-full text-left font-mono text-[9px] border-collapse"><thead class="bg-slate-50 sticky top-0 border-b"><tr><th class="p-2 border-r uppercase tracking-tighter">Time Line</th><th class="p-2 border-r text-center">TMin</th><th class="p-2 border-r text-center">TMax</th><th class="p-2 text-center text-green-700 italic font-black uppercase">NF</th></tr></thead><tbody>';
                    d_j.pre_view.forEach(ro_obj => { 
                        prevTabH += `<tr class="border-b"><td class="p-2 border-r uppercase text-slate-500">${ro_obj.Data}</td><td class="p-2 border-r text-center font-bold">${ro_obj.Tmin}</td><td class="p-2 border-r text-center font-bold">${ro_obj.Tmax}</td><td class="p-2 text-center text-green-700 font-bold">${ro_obj.NF}</td></tr>`; 
                    });
                    document.getElementById('sanit-preview').innerHTML = prevTabH + '</tbody></table>';

                    window.scrollTo({top: document.body.scrollHeight, behavior:'smooth'});
                } catch(e) {
                    alert("ALERTA CIENTÍFICO: Falha interna no motor de análise.\\nMotivo: " + e.message);
                } finally { document.getElementById('loader').classList.add('hidden'); }
            }

            function baixarDoc() {
                if(!b64File) return;
                const binaryStr = atob(b64File), buffer = new ArrayBuffer(binaryStr.length), uint8 = new Uint8Array(buffer);
                for(let i=0; i<binaryStr.length; i++) uint8[i] = binaryStr.charCodeAt(i);
                const bO = new Blob([buffer], {type:'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'});
                const linkU = document.createElement('a'); linkU.href = window.URL.createObjectURL(bO);
                linkU.download = `Investigacao_Tb_Resultados.xlsx`; linkU.click();
            }
        </script>
        <style>.sheet-input { width:100%; border:none; padding:4px; font-family:monospace; text-align:center; }</style>
    </body>
    </html>
    """.replace("URL_VAL", SURL).replace("KEY_VAL", SKEY)
    return html_src

# =========================================================================
# ⚙️ BLOCO 4: ENGINE AGRO-LAB V4 (ANTIPANIC DATA IMPORT)
# =========================================================================
@app.post("/api/agro/calculate/pro")
async def handle_scientific_calculation(
    file: UploadFile = None, dataset_manual: str = Form(None), label: str = Form(""),
    vmin_a: float = Form(0.0), vmax_a: float = Form(20.0), vstep_a: float = Form(0.5)
):
    try:
        # Load dinâmico sem restrição de pattern (Regex relaxado no read_csv)
        if file:
            content = await file.read()
            df = pd.read_csv(BytesIO(content), sep=None, engine='python', decimal=',') if file.filename.endswith('.csv') else pd.read_excel(BytesIO(content))
        else:
            # Separador PIPE para não bater com vírgula do decimal e ponto do milhar
            df = pd.read_csv(StringIO(dataset_manual), sep='|', names=['Data','Tmin','Tmax','NF'], header=None)

        # Standardizing ColNames (Data, Tmin, Tmax, NF)
        df.rename(columns=lambda x: 'Data' if fix_scientific_txt(x) == 'data' else x, inplace=True)
        df.rename(columns=lambda x: 'Tmin' if fix_scientific_txt(x) in ['tmin','tmín','tminima'] else x, inplace=True)
        df.rename(columns=lambda x: 'Tmax' if fix_scientific_txt(x) in ['tmax','tmáx','tmaxima'] else x, inplace=True)
        df.rename(columns=lambda x: 'NF' if fix_scientific_txt(x) in ['nf','variavel','variável','nfmedio'] else x, inplace=True)

        # Higiene Numérica "Atômica": remove símbolos e tenta converter em número
        for cn in ['Tmin','Tmax','NF']:
            if cn in df.columns:
                df[cn] = pd.to_numeric(df[cn].astype(str).str.replace(',', '.').str.replace('[^0-9\\.\\-]', '', regex=True), errors='coerce')
        
        # Filtro de Data - Testa sem "travar" com padrão estrito
        df['Data'] = pd.to_datetime(df['Data'], dayfirst=True, errors='coerce')
        
        # Só mantemos o que o Python identificou com sucesso (limpa cabeçalhos repetidos e linhas sujas)
        df = df.dropna(subset=['Data','Tmin','Tmax']).sort_values('Data').reset_index(drop=True)

        # Isolamos o dataset de regressão (dias onde a Variável existe)
        exp_dataset = df.dropna(subset=['NF'])
        if len(exp_dataset) < 3:
            raise ValueError(f"Foram encontradas apenas {len(exp_dataset)} medições da Variável (NF). O sistema exige pelo menos 3 medições de campo válidas em datas diferentes.")

        # Calculando matriz de regressão térmica
        df['Tmed'] = (df['Tmin'] + df['Tmax']) / 2
        obs_idx = exp_dataset.index
        scan_records = []
        winner_rec = {}
        abs_low_err = float('inf')

        # Escaneamento das Tbs
        search_range = np.arange(vmin_a, vmax_a + vstep_a, vstep_a)
        for ti in search_range:
            ti = round(float(ti), 2)
            sta_curr = (df['Tmed'] - ti).clip(lower=0).cumsum()
            
            # Sub-amostra Sincronizada (X e y devem ter o mesmo tamanho baseado no exp_index)
            X_engine = sta_curr.loc[obs_idx].values.reshape(-1, 1)
            y_engine = df.loc[obs_idx, 'NF'].values
            
            lr_model = LinearRegression().fit(X_engine, y_engine)
            qme_s = mean_squared_error(y_engine, lr_model.predict(X_engine))
            r2_s = lr_model.score(X_engine, y_engine)
            scan_records.append({'Tb': ti, 'R2': r2_s, 'QME': qme_s})
            
            if qme_s < abs_low_err:
                abs_low_err = qme_s
                winner_rec = {
                    'tb': ti, 'r2': r2_s, 'qme': qme_s, 'slope': lr_model.coef_[0], 'int': lr_model.intercept_,
                    'plt_x': sta_curr.loc[obs_idx].tolist(), 'full_sta': sta_curr.tolist()
                }

        log_err_df = pd.DataFrame(scan_records)
        
        # Planilhas para Exportação Excel
        clima_exp = df[['Data','Tmin','Tmax','Tmed']].copy()
        clima_exp['STa_Referencia'] = winner_rec['full_sta']
        pheno_exp = pd.DataFrame({'Data': df.loc[obs_idx, 'Data'], 'NF_Experimental': df.loc[obs_idx, 'NF'], 'STa_Modelo_Ideal': winner_rec['plt_x']})

        # Encapsula o arquivo pronto em Base64
        xls_base64 = build_academic_excel_pkg(clima_exp, log_err_df, pheno_exp, winner_rec['tb']) if 'build_academic_excel_pkg' in locals() else build_excel_output(clima_exp, log_err_df, pheno_exp, winner_rec['tb'])

        return {
            "identificacao": label or "Scientific Output Lab",
            "output": {"tb_opt": winner_rec['tb'], "r2_opt": winner_rec['r2'], "qme_opt": winner_rec['qme']},
            "charts": {
                "qx": log_err_df['Tb'].tolist(), "qy": log_err_df['QME'].tolist(),
                "rx": [float(vi) for vi in winner_rec['plt_x']],
                "ry": exp_dataset['NF'].astype(float).tolist(),
                "rp": [float(vi * winner_rec['slope'] + winner_rec['int']) for vi in winner_rec['plt_x']]
            },
            "pre_view": df.head(30).astype(str).to_dict(orient="records"),
            "xlsx_64": xls_base64
        }
    except Exception as general_ex:
        import traceback
        print(traceback.format_exc())
        return {"detail": str(general_ex)}

# Ajuste do nome da função de Excel caso ocorra mismatch de nomenclatura nas versões enviadas anteriormente
def build_excel_output(c, e, p, tb):
    return build_academic_excel(c, e, p, tb) if 'build_academic_excel' in locals() else build_xlsx(c, e, p, tb)
