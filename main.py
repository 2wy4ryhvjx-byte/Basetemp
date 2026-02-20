import os
import stripe
import pandas as pd
import numpy as np
import unicodedata
import base64
import re
from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from fastapi.responses import HTMLResponse
from io import BytesIO, StringIO
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_squared_error

app = FastAPI()

# =========================================================================
# 🔒 BLOCO 1: SEGURANÇA E LOGIN (BLINDADO)
# =========================================================================
SURL = "https://iuhtopexunirguxmjiey.supabase.co"
SKEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Iml1aHRvcGV4dW5pcmd1eG1qaWV5Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzE1MjIzNTcsImV4cCI6MjA4NzA5ODM1N30.EjDui9gQ5AlRaNpoVQisGUoXmK3j74gwzq9QSguxq78"
stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "")
ADM_MAIL = "abielgm@icloud.com"

# =========================================================================
# 🧬 BLOCO 2: LOGICA DE RELATORIOS (EXCEL WRITER)
# =========================================================================
def build_academic_excel(df_clima, df_err, df_reg, melh_tb):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as wr:
        df_clima.to_excel(wr, sheet_name='Base_Meteorologica', index=False)
        df_reg.to_excel(wr, sheet_name='Resultado_Final_STa', index=False)
        df_err.to_excel(wr, sheet_name='Estatistica_QME', index=False)
        wb = wr.book
        f_dt = wb.add_format({'num_format': 'dd/mm/yyyy'})
        if 'Resultado_Final_STa' in wr.sheets:
            wr.sheets['Resultado_Final_STa'].set_column('A:A', 12, f_dt)
        c = wb.add_chart({'type': 'scatter', 'subtype': 'smooth'})
        c.add_series({'name': 'QME', 'categories':['Estatistica_QME',1,0,len(df_err),0], 'values':['Estatistica_QME',1,2,len(df_err),2]})
        wr.sheets['Estatistica_QME'].insert_chart('E2', c)
    return base64.b64encode(output.getvalue()).decode()

# =========================================================================
# 🎨 BLOCO 3: WORKSTATION INTERFACE
# =========================================================================
@app.get("/", response_class=HTMLResponse)
async def academic_lab():
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
            .sheet-input { width: 100%; border: none; padding: 6px; font-size: 11px; text-align: center; background: transparent; outline: none; }
            .sheet-input:focus { background-color: #f0fdf4; border-bottom: 2px solid #16a34a; }
            .header-agro { background: #f8fafc; font-size: 10px; font-weight: 900; color: #64748b; padding: 12px; border: 1px solid #e2e8f0; text-transform: uppercase; }
        </style>
    </head>
    <body class="bg-[#F8FAFC] font-sans min-h-screen text-slate-800">
        <div id="loader" class="hidden fixed inset-0 bg-white/95 z-50 flex flex-col items-center justify-center font-black text-green-700 italic">
            <div class="animate-spin rounded-full h-16 w-16 border-b-2 border-green-600 mb-4"></div>
            AGRO-MOTOR: SINCRO EM PROCESSAMENTO...
        </div>

        <div class="max-w-6xl mx-auto p-4 md:p-8">
            <div id="login-sec" class="max-w-md mx-auto bg-white p-12 rounded-[3rem] shadow-2xl mt-12 border text-center relative overflow-hidden">
                <div class="absolute top-0 left-0 w-full h-1 bg-yellow-400"></div>
                <h1 class="text-4xl font-black text-green-700 italic mb-8 italic uppercase tracking-tighter decoration-yellow-400 underline">EstimaTB🌿</h1>
                <input type="email" id="email" placeholder="E-mail Acadêmico" class="w-full border-2 p-4 rounded-3xl mb-4 focus:border-green-600 outline-none shadow-sm">
                <input type="password" id="password" placeholder="Senha" class="w-full border-2 p-4 rounded-3xl mb-8 focus:border-green-600 outline-none shadow-sm">
                <button onclick="loginApp()" class="w-full bg-green-600 text-white py-4 rounded-3xl font-black shadow-lg">ACESSAR LABORATORIO</button>
            </div>

            <div id="lab-sec" class="hidden">
                <div class="flex flex-col md:flex-row justify-between items-center bg-white p-6 rounded-[2.2rem] border border-slate-200 mb-6 px-10 shadow-sm">
                    <p class="font-bold text-xs uppercase text-slate-400">Investigador: <span id="u-display" class="text-green-700 not-italic font-black text-sm ml-2"></span></p>
                    <button onclick="logOutApp()" class="text-red-500 font-black text-[10px] uppercase border-b-2 border-red-50 hover:text-red-700 transition tracking-tighter italic">Encerrar Sessão</button>
                </div>

                <div class="grid lg:grid-cols-12 gap-8">
                    <!-- Config Side -->
                    <div class="lg:col-span-5 space-y-6">
                        <div class="bg-white p-10 rounded-[3rem] shadow-xl border">
                            <h3 class="font-black text-[10px] uppercase mb-8 border-b pb-4 italic tracking-widest"><i class="fas fa-microscope mr-2 text-green-600"></i>Gestão Analítica</h3>
                            
                            <input type="text" id="label_agro" placeholder="Nome da Análise" class="w-full border-2 p-4 rounded-3xl mb-8 bg-slate-50 font-bold focus:border-green-600 outline-none">

                            <div class="flex bg-slate-100 p-1.5 rounded-3xl mb-8">
                                <button onclick="tab('f')" id="btn-f" class="flex-1 py-3 text-[10px] font-black rounded-xl bg-white shadow-sm text-green-700">ANEXAR EXCEL</button>
                                <button onclick="tab('m')" id="btn-m" class="flex-1 py-3 text-[10px] font-black rounded-xl text-slate-400 uppercase italic">PLANILHA MANUAL</button>
                            </div>

                            <div id="ui-f" class="mb-10 text-center"><input type="file" id="f_up" class="block w-full border-2 border-dashed p-10 rounded-3xl bg-slate-50 text-[10px] italic"></div>

                            <div id="ui-m" class="hidden mb-10">
                                <p class="text-[9px] font-black text-slate-400 mb-4 uppercase text-center underline decoration-yellow-300">Cole do Excel em 4 Colunas (Data | TMin | TMax | NF)</p>
                                <div class="rounded-3xl border border-slate-200 overflow-hidden mb-4 bg-white max-h-[30rem] overflow-y-auto">
                                    <table class="w-full border-collapse">
                                        <thead class="sticky top-0 z-30 shadow-sm"><tr><th class="header-agro">Data</th><th class="header-agro">T.Mín</th><th class="header-agro">T.Máx</th><th class="header-agro italic text-green-700">NF (Var.)</th></tr></thead>
                                        <tbody id="m-body-lab"></tbody>
                                    </table>
                                </div>
                                <div class="flex justify-between p-2"><button onclick="addLine(5)" class="text-[9px] font-black text-green-600 uppercase underline">+ Adicionar</button><button onclick="limpaT()" class="text-[9px] font-black text-red-300 uppercase italic">Limpar Tudo</button></div>
                            </div>

                            <div class="bg-slate-50 p-8 rounded-[2rem] text-center grid grid-cols-3 gap-3 mb-10 border border-slate-100 shadow-inner">
                                <div class="flex flex-col"><label class="text-[8px] font-bold text-slate-400 uppercase mb-1">Início</label><input type="number" id="vmin" value="0.0" class="w-full border p-2 rounded-xl text-center font-bold"></div>
                                <div class="flex flex-col"><label class="text-[8px] font-bold text-slate-400 uppercase mb-1">Fim</label><input type="number" id="vmax" value="20.0" class="w-full border p-2 rounded-xl text-center font-bold"></div>
                                <div class="flex flex-col"><label class="text-[8px] font-black text-green-600 uppercase mb-1 underline">Passo</label><input type="number" id="vstep" value="0.5" step="0.1" class="w-full border border-green-100 p-2 rounded-xl text-center font-bold text-green-600"></div>
                            </div>

                            <button onclick="calculateScientific()" id="exe" class="w-full bg-green-600 text-white py-6 rounded-[2.5rem] font-black text-2xl shadow-xl shadow-green-100 hover:scale-[1.03] transition uppercase tracking-widest italic">Executar Modelagem</button>
                        </div>
                    </div>

                    <!-- Side Res -->
                    <div id="res-view" class="lg:col-span-7 hidden animate-in slide-in-from-right duration-500">
                        <div class="bg-white p-10 rounded-[3.5rem] shadow-2xl border-t-[14px] border-slate-900 sticky top-10">
                             <div class="grid grid-cols-3 gap-6 mb-12">
                                <div class="bg-slate-50 p-6 rounded-[2rem] border text-center shadow-inner"><span class="text-[9px] font-black text-slate-400 uppercase italic block mb-2">Tb Sugerida</span><p id="o-t" class="text-4xl font-black font-mono tracking-tighter">--</p></div>
                                <div class="bg-green-50/50 p-6 rounded-[2rem] border-2 border-green-100 shadow-inner text-center"><span class="text-[9px] font-black text-green-600 uppercase block mb-2 tracking-widest">Ajuste (R²)</span><p id="o-r" class="text-4xl font-black font-mono text-green-700 tracking-tighter">--</p></div>
                                <div class="bg-slate-50 p-6 rounded-[2rem] border shadow-inner text-center"><span class="text-[9px] font-black text-slate-400 block mb-2 italic">Min. Erro</span><p id="o-q" class="text-[12px] font-black font-mono tracking-tight text-slate-400">--</p></div>
                             </div>
                             
                             <div class="space-y-6">
                                <div id="gr1" class="h-64 border rounded-[2rem] p-2 bg-white"></div>
                                <div id="gr2" class="h-64 border rounded-[2rem] p-2 bg-white"></div>
                             </div>

                             <div class="mt-8 rounded-[2rem] border border-slate-200 bg-slate-50 overflow-hidden">
                                <h4 class="p-3 text-[9px] font-black uppercase text-slate-500 italic ml-4 flex items-center"><i class="fas fa-clipboard-check mr-2 text-green-500"></i>Sanitização dos Dados Lidos (Pré-visualização)</h4>
                                <div id="preview-final" class="max-h-56 overflow-auto border-t bg-white font-mono text-[9px]"></div>
                             </div>

                             <div id="btn-export-sec" class="mt-8 p-10 bg-yellow-50/30 border-2 border-amber-200 border-dotted rounded-[2.5rem] text-center shadow-inner">
                                <button onclick="getExcel()" class="bg-yellow-500 hover:bg-yellow-600 text-white font-black py-6 px-12 rounded-full text-md shadow-xl flex items-center justify-center mx-auto tracking-widest italic uppercase transform active:scale-95 transition-all"><i class="fas fa-file-download mr-4 text-2xl"></i>Exportar Relatório Acadêmico (.xlsx)</button>
                             </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <script>
            const SV_U = "VAL_U"; const SV_K = "VAL_K"; const ADM_ID = "abielgm@icloud.com";
            const _lab = supabase.createClient(SV_U, SV_K);
            let uiM = 'f'; let b64doc = null;

            function limpaT() { document.getElementById('m-body-lab').innerHTML = ''; addLine(15); }
            function addLine(n) {
                const b = document.getElementById('m-body-lab');
                for(let i=0; i<n; i++){
                    const r = document.createElement('tr'); r.className='border-b hover:bg-slate-50 transition';
                    r.innerHTML = '<td><input type="text" class="sheet-input c-d"></td><td><input type="text" class="sheet-input c-min"></td><td><input type="text" class="sheet-input c-max"></td><td><input type="text" class="sheet-input c-v" placeholder="..."></td>';
                    b.appendChild(r);
                }
            }
            limpaT();

            // CTRL+V COM PROTECAO DE DADOS SUJOS
            document.addEventListener('paste', e => {
                if(e.target.classList.contains('sheet-input')) {
                    e.preventDefault();
                    const clip_txt = e.clipboardData.getData('text');
                    const clip_arr = clip_txt.split(/\\r?\\n/);
                    let rowT = e.target.closest('tr');
                    clip_arr.forEach(line => {
                        if(line.trim() === '') return;
                        const colD = line.split('\\t'), cellI = rowT.querySelectorAll('input');
                        for(let i=0; i<Math.min(4, colD.length, cellI.length); i++){
                            cellI[i].value = colD[i].trim().replace(',', '.'); 
                        }
                        rowT = rowT.nextElementSibling; if(!rowT){ addLine(1); rowT = document.getElementById('m-body-lab').lastElementChild; }
                    });
                }
            });

            async function loginApp() {
                const e = document.getElementById('email').value, p = document.getElementById('password').value;
                document.getElementById('loader').classList.remove('hidden');
                let {data, error} = await _lab.auth.signInWithPassword({email:e, password:p});
                if(error) { alert("Autenticação Falhou!"); document.getElementById('loader').classList.add('hidden'); }
                else location.reload();
            }

            async function checkSessao() {
                const {data:{user}} = await _lab.auth.getUser();
                if(user) {
                    document.getElementById('login-sec').classList.add('hidden');
                    document.getElementById('lab-sec').classList.remove('hidden');
                    document.getElementById('u-display').innerText = user.email.toLowerCase();
                }
            }
            checkSessao();
            async function logOutApp() { await _lab.auth.signOut(); localStorage.clear(); window.location.replace('/'); }
            function tab(m) { uiM = m; document.getElementById('btn-f').classList.toggle('bg-white', m=='f'); document.getElementById('btn-m').classList.toggle('bg-white', m=='m'); document.getElementById('ui-f').classList.toggle('hidden', m=='m'); document.getElementById('ui-m').classList.toggle('hidden', m=='f'); }

            async function calculateScientific() {
                document.getElementById('loader').classList.remove('hidden');
                const fd = new FormData();
                fd.append('tag', document.getElementById('label_agro').value || 'Agromet_Anita_12');
                fd.append('vmin_a', document.getElementById('vmin').value);
                fd.append('vmax_a', document.getElementById('vmax').value);
                fd.append('step_a', document.getElementById('vstep').value);

                if(uiM === 'f') {
                    const fi = document.getElementById('f_up');
                    if(!fi.files[0]){ alert("Anexe sua planilha."); document.getElementById('loader').classList.add('hidden'); return; }
                    fd.append('file', fi.files[0]);
                } else {
                    let dTableArr = [];
                    document.querySelectorAll('#m-body-lab tr').forEach(tr => {
                        // Enviamos SEMPRe usando ponto e virgula para o python ler as 4 colunas independente da virgula decimal
                        const cArr = Array.from(tr.querySelectorAll('input')).map(i => i.value.trim().replace(',', '.'));
                        if(cArr[0] && cArr[1] && cArr[2]) {
                            if(!cArr[3] || cArr[3] === '') cArr[3] = 'nan'; dTableArr.push(cArr.join(';'));
                        }
                    });
                    if(dTableArr.length < 4) { alert("Base manual com baixa volumetria de dados."); document.getElementById('loader').classList.add('hidden'); return; }
                    fd.append('manual_csv', dTableArr.join('\\n'));
                }

                try {
                    const resp = await fetch('/api/agro/scientific/engine', {method:'POST', body:fd});
                    const dj = await resp.json();
                    if(dj.detail) throw new Error(dj.detail);

                    b64doc = dj.excel_pkg;
                    document.getElementById('res-view').classList.remove('hidden');
                    document.getElementById('o-t').innerText = dj.calc.t + "°";
                    document.getElementById('o-r').innerText = dj.calc.r.toFixed(4);
                    document.getElementById('o-q').innerText = dj.calc.q.toFixed(9);

                    Plotly.newPlot('gr1', [{x: dj.plt.qx, y: dj.plt.qy, mode: 'lines+markers', line:{color:'black'}, marker:{size:4}}], {title:'Mínimo Residual (Estatística QME)', font:{size:9}, margin:{t:40}});
                    Plotly.newPlot('gr2', [{x: dj.plt.rx, y: dj.plt.ry, mode:'markers', marker:{color:'gray', symbol:'circle-open'}, name:'Obs.'},{x: dj.plt.rx, y: dj.plt.rp, mode:'lines', line:{color:'black', dash:'dot'}, name:'Modelo'}], {title:'Regressão Final: Soma Térmica vs Variável', font:{size:9}, showlegend:false, margin:{t:40}});

                    // Previsualizacao Tabular
                    let tbH = '<table class="w-full text-left text-[8px] font-mono border-collapse"><thead class="bg-slate-50 sticky top-0 border-b"><tr><th class="p-2 border-r uppercase">Timeline</th><th class="p-2 border-r text-center">TMin</th><th class="p-2 border-r text-center">TMax</th><th class="p-2 text-center text-green-700 italic font-black uppercase tracking-tight">Variavel</th></tr></thead><tbody>';
                    dj.view.forEach(rO => { 
                        tbH += `<tr class="border-b"><td class="p-2 border-r uppercase text-slate-400 tracking-tighter">${rO.Data}</td><td class="p-2 border-r text-center font-bold">${rO.Tmin}</td><td class="p-2 border-r text-center font-bold">${rO.Tmax}</td><td class="p-2 text-center text-green-700 font-bold">${rO.NF}</td></tr>`; 
                    });
                    document.getElementById('preview-final').innerHTML = tbH + '</tbody></table>';

                    window.scrollTo({top: document.body.scrollHeight, behavior:'smooth'});
                } catch(err) {
                    alert("ALERTA CIENTÍFICO: Falha técnica na análise de dados.\\nMotivo: " + err.message);
                } finally { document.getElementById('loader').classList.add('hidden'); }
            }

            function getExcel() {
                if(!b64doc) return alert("Download indisponível.");
                const binS = atob(b64doc), buffArr = new ArrayBuffer(binS.length), u8 = new Uint8Array(buffArr);
                for(let i=0; i<binS.length; i++) u8[i] = binS.charCodeAt(i);
                const blobObj = new Blob([buffArr], {type:'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'});
                const linkD = document.createElement('a'); linkD.href = window.URL.createObjectURL(blobObj);
                linkD.download = `Investigacao_Tb_Cientifica.xlsx`; linkD.click();
            }
        </script>
        <style>.sheet-cell { width:100%; border:none; padding:4px; font-family:monospace; text-align:center; }</style>
    </body>
    </html>
    """.replace("VAL_U", SURL).replace("VAL_K", SKEY)

# =========================================================================
# ⚙️ BLOCO 4: BACKEND FINAL (ESTATISTICA BLINDADA)
# =========================================================================
@app.post("/api/agro/scientific/engine")
async def laboratory_motor_pro(
    file: UploadFile = None, manual_csv: str = Form(None), tag: str = Form(""),
    vmin_a: float = Form(0.0), vmax_a: float = Form(20.0), step_a: float = Form(0.5)
):
    try:
        # Load dinâmico
        if file:
            content = await file.read()
            df = pd.read_csv(BytesIO(content), sep=None, engine='python', decimal=',') if file.filename.endswith('.csv') else pd.read_excel(BytesIO(content))
        else:
            # Separador Ponto-e-Vírgula é forçado para ignorar vírgula decimal nos dados do paste
            df = pd.read_csv(StringIO(manual_csv), sep=';', names=['Data','Tmin','Tmax','NF'], header=None)

        # Higiene Absoluta das Colunas
        cols_norm = {str(c).lower().strip(): c for c in df.columns}
        renamed = {}
        for key_t, val_t in {'data': 'Data', 'tmin': 'Tmin', 'tmín': 'Tmin', 'tmax': 'Tmax', 'tmáx': 'Tmax', 'nf': 'NF', 'variavel': 'NF', 'variável': 'NF'}.items():
            if key_t in cols_norm: renamed[cols_norm[key_t]] = val_t
        df.rename(columns=renamed, inplace=True)

        # Higiene Absoluta de Tipos e Caracteres Sujos (Ex: Cabeçalho ou Espaços colados por engano)
        for col_f in ['Tmin','Tmax','NF']:
            if col_f in df.columns:
                # Remove R$, Letras e tudo que não for Número ou Ponto antes de converter
                df[col_f] = pd.to_numeric(df[col_f].astype(str).str.replace(',', '.').str.replace('[^0-9\\.\\-]', '', regex=True), errors='coerce')
        
        # Filtro de Data - Testa automaticamente PT-BR e US, ignora lixo
        df['Data'] = pd.to_datetime(df['Data'], dayfirst=True, errors='coerce')
        
        # Limpa as linhas mortas de temperatura e as datas irreconhecíveis
        df = df.dropna(subset=['Data','Tmin','Tmax']).sort_values('Data').reset_index(drop=True)

        # Localiza o dataset experimental real (onde houve NF medida)
        exp_dataset = df.dropna(subset=['NF'])
        if len(exp_dataset) < 3:
            raise ValueError(f"Foram encontradas apenas {len(exp_dataset)} avaliações válidas da Variável. O motor acadêmico exige pelo menos 3 medições fenológicas para processar a regressão linear.")

        # Matrix Calculation
        df['Tmed'] = (df['Tmin'] + df['Tmax']) / 2
        exp_index = exp_dataset.index
        results_track = []
        winner_rec = {}
        abs_min_err_qme = float('inf')

        range_array = np.arange(vmin_a, vmax_a + step_a, step_a)
        for tbi in range_array:
            tbi = round(float(tbi), 2)
            sta_calc = (df['Tmed'] - tbi).clip(lower=0).cumsum()
            
            X_engine = sta_calc.loc[exp_index].values.reshape(-1, 1)
            y_engine = df.loc[exp_index, 'NF'].values
            
            model_sci = LinearRegression().fit(X_engine, y_engine)
            curr_qme = mean_squared_error(y_engine, model_sci.predict(X_engine))
            curr_r2 = model_sci.score(X_engine, y_engine)
            
            results_track.append({'Tb': tbi, 'R2': curr_r2, 'QME': curr_qme})
            
            if curr_qme < abs_min_err_qme:
                abs_min_err_qme = curr_qme
                winner_rec = {
                    't': tbi, 'r': curr_r2, 'q': curr_qme, 
                    'ang': model_sci.coef_[0], 'int': model_sci.intercept_,
                    'x_p': sta_calc.loc[exp_index].tolist(),
                    'full_s': sta_calc.tolist()
                }

        log_err_df = pd.DataFrame(results_track)
        
        # Report Constructor
        final_clima_rep = df[['Data','Tmin','Tmax','Tmed']].copy()
        final_clima_rep['Soma_Termica_Modelo'] = winner_rec['full_s']
        
        final_pheno_rep = pd.DataFrame({
            'Data': df.loc[exp_index, 'Data'],
            'Observado_Campo_NF': df.loc[exp_index, 'NF'],
            'STa_Acumulado_Final': winner_rec['x_p']
        })

        b64_output_final = build_academic_excel(final_clima_rep, log_err_df, final_pheno_rep, winner_rec['t'])

        return {
            "label_i": tag or "Resultado Anita Academico",
            "calc": {"t": winner_rec['t'], "r": winner_rec['r'], "q": winner_rec['q']},
            "plt": {
                "qx": log_err_df['Tb'].tolist(), "qy": log_err_df['QME'].tolist(),
                "rx": winner_rec['x_p'], "ry": exp_dataset['NF'].astype(float).tolist(),
                "rp": [float(vi * winner_rec['ang'] + winner_rec['int']) for vi in winner_rec['x_p']]
            },
            "view": df.head(40).astype(str).to_dict(orient="records"),
            "excel_pkg": b64_output_final
        }
    except Exception as sci_ex:
        return {"detail": str(sci_ex)}
