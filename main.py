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
# 🔒 BLOCO 1: LOGIN E SEGURANÇA (BLINDADO - NÃO ALTERAR)
# =========================================================================
SURL = "https://iuhtopexunirguxmjiey.supabase.co"
SKEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Iml1aHRvcGV4dW5pcmd1eG1qaWV5Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzE1MjIzNTcsImV4cCI6MjA4NzA5ODM1N30.EjDui9gQ5AlRaNpoVQisGUoXmK3j74gwzq9QSguxq78"
stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "")
ADM_MAIL = "abielgm@icloud.com"

# =========================================================================
# 🧬 BLOCO 2: AUXILIARES E EXCEL (LOGICA DE SAIDA)
# =========================================================================
def fix_sc(t):
    if not isinstance(t, str): return t
    return "".join(c for c in unicodedata.normalize('NFKD', t) if not unicodedata.combining(c)).lower().strip()

def export_to_xls(clima_df, error_df, reg_df, final_tb):
    out = BytesIO()
    with pd.ExcelWriter(out, engine='xlsxwriter') as wr:
        clima_df.to_excel(wr, sheet_name='Série_Meteorologica', index=False)
        reg_df.to_excel(wr, sheet_name='Regressao_NF_vs_STa', index=False)
        error_df.to_excel(wr, sheet_name='Tabela_QME', index=False)
        book = wr.book
        dt_f = book.add_format({'num_format': 'dd/mm/yyyy'})
        if 'Regressao_NF_vs_STa' in wr.sheets:
            wr.sheets['Regressao_NF_vs_STa'].set_column('A:A', 12, dt_f)
        c = book.add_chart({'type': 'scatter', 'subtype': 'smooth'})
        c.add_series({'name':'QME vs Tb', 'categories':['Tabela_QME',1,0,len(error_df),0], 'values':['Tabela_QME',1,2,len(error_df),2]})
        wr.sheets['Tabela_QME'].insert_chart('E2', c)
    return base64.b64encode(out.getvalue()).decode()

# =========================================================================
# 🎨 BLOCO 3: INTERFACE DE TRABALHO (ESTÁVEL)
# =========================================================================
@app.get("/", response_class=HTMLResponse)
async def lab_ui():
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
            .lab-input { width: 100%; border: none; padding: 6px; font-size: 11px; font-family: monospace; text-align: center; background: transparent; outline: none; }
            .lab-input:focus { background-color: #f0fdf4; box-shadow: inset 0 0 0 2px #16a34a; }
            .th-sci { background: #f8fafc; font-size: 10px; font-weight: 900; color: #64748b; padding: 12px; border: 1px solid #e2e8f0; text-transform: uppercase; }
        </style>
    </head>
    <body class="bg-slate-50 font-sans min-h-screen text-slate-800">
        <div id="loading" class="hidden fixed inset-0 bg-white/95 z-50 flex flex-col items-center justify-center font-black text-green-700 italic">
            <div class="animate-spin rounded-full h-16 w-16 border-t-4 border-green-600 mb-4 shadow-xl"></div>
            AGRO-MOTOR EM PROCESSAMENTO...
        </div>

        <div class="max-w-6xl mx-auto p-4 md:p-10">
            <!-- SEÇÃO LOGIN -->
            <div id="login-sec" class="max-w-md mx-auto bg-white p-12 rounded-[3.5rem] shadow-2xl mt-12 border border-slate-200 text-center relative overflow-hidden">
                <div class="absolute top-0 left-0 w-full h-2 bg-yellow-400"></div>
                <h1 class="text-4xl font-black text-green-700 italic mb-2 tracking-tighter uppercase decoration-yellow-400 underline decoration-4">EstimaTB🌿</h1>
                <p class="text-[9px] font-bold text-slate-300 uppercase tracking-widest mb-10 italic">Academic Clear-Gate</p>
                <div class="space-y-4">
                    <input type="email" id="email" placeholder="E-mail" class="w-full border-2 p-4 rounded-3xl outline-none focus:border-green-600 bg-slate-50 text-sm">
                    <input type="password" id="password" placeholder="Senha" class="w-full border-2 p-4 rounded-3xl outline-none focus:border-green-600 bg-slate-50 text-sm">
                    <button onclick="authLog()" class="w-full bg-green-600 text-white py-5 rounded-3xl font-black shadow-xl hover:bg-green-700">ENTRAR NO SISTEMA</button>
                    <button onclick="toggleR()" id="s-btn" class="text-green-600 font-bold text-[9px] uppercase mt-4">Novo Cadastro</button>
                </div>
            </div>

            <!-- DASHBOARD LAB -->
            <div id="main-lab" class="hidden animate-in fade-in duration-700">
                <div class="flex flex-col md:flex-row justify-between items-center bg-white p-6 rounded-[2.5rem] border mb-10 px-10 shadow-sm">
                    <p class="font-bold text-[10px] uppercase text-slate-400 italic">Investigação Ativa: <span id="u-user" class="text-green-700 font-black not-italic ml-1"></span></p>
                    <button onclick="labExit()" class="text-red-500 font-black text-[10px] uppercase underline transition-all">Sair</button>
                </div>

                <div class="grid lg:grid-cols-12 gap-8">
                    <div class="lg:col-span-5 space-y-6">
                        <div class="bg-white p-8 rounded-[3.5rem] shadow-xl border">
                            <h3 class="font-black text-[10px] uppercase mb-8 border-b pb-4 flex items-center italic tracking-widest text-slate-600 italic underline decoration-green-200"><i class="fas fa-file-csv mr-2 text-green-600"></i>Gestão de Amostra</h3>
                            
                            <label class="text-[9px] font-black text-slate-400 ml-2 mb-1 block uppercase italic">Nome da Análise</label>
                            <input type="text" id="a_nome" placeholder="Ex:Anita Época 12" class="w-full border-2 p-4 rounded-3xl mb-8 font-bold bg-slate-50 outline-none focus:border-green-500 text-sm">

                            <div class="flex bg-slate-100 p-1 rounded-2xl mb-8 border shadow-inner">
                                <button onclick="tab('f')" id="b-f" class="flex-1 py-3 text-[10px] font-black rounded-xl bg-white shadow-sm text-green-700 uppercase">Anexar Arquivo</button>
                                <button onclick="tab('m')" id="b-m" class="flex-1 py-3 text-[10px] font-black rounded-xl text-slate-400 uppercase tracking-tighter">Inserir Grade</button>
                            </div>

                            <div id="ui-f" class="mb-10 text-center"><input type="file" id="f-in" class="block w-full border-2 border-dashed p-10 rounded-[2.5rem] bg-slate-50 cursor-pointer text-xs"></div>

                            <div id="ui-m" class="hidden mb-10">
                                <div class="rounded-3xl border border-slate-200 overflow-hidden bg-white mb-2 max-h-96 overflow-y-auto">
                                    <table class="w-full border-collapse">
                                        <thead class="sticky top-0 z-20"><tr><th class="th-sci">Data</th><th class="th-sci">Mín</th><th class="th-sci">Máx</th><th class="th-sci italic text-green-600 font-bold uppercase italic">Variável</th></tr></thead>
                                        <tbody id="grid-lab-body"></tbody>
                                    </table>
                                </div>
                                <div class="flex justify-between px-2"><button onclick="addLabRow(10)" class="text-[9px] font-black text-green-600 uppercase underline">+ Linhas</button><button onclick="clearLabTable()" class="text-[9px] font-black text-red-300">Zerar</button></div>
                            </div>

                            <div class="bg-slate-50 p-6 rounded-3xl text-center grid grid-cols-3 gap-3 mb-10 border shadow-inner">
                                <div><label class="text-[8px] font-bold block mb-1">Mín (°C)</label><input type="number" id="v-min" value="0.0" class="w-full border p-2 rounded-xl text-center font-bold"></div>
                                <div><label class="text-[8px] font-bold block mb-1">Máx (°C)</label><input type="number" id="v-max" value="20.0" class="w-full border p-2 rounded-xl text-center font-bold"></div>
                                <div><label class="text-[8px] font-bold block mb-1 text-green-600 italic">Passo</label><input type="number" id="v-step" value="0.5" step="0.1" class="w-full border border-green-200 p-2 rounded-xl text-center font-bold text-green-600"></div>
                            </div>

                            <button onclick="startAnalyticProcess()" id="execBtn" class="w-full bg-green-600 text-white py-6 rounded-[2.5rem] font-black text-xl shadow-xl hover:scale-105 transition tracking-widest uppercase italic italic underline decoration-yellow-400 decoration-2">Executar Modelagem</button>
                        </div>
                    </div>

                    <div id="results-sec" class="lg:col-span-7 hidden animate-in slide-in-from-right duration-500">
                        <div class="bg-white p-10 rounded-[3.5rem] shadow-2xl border-t-[14px] border-slate-900 sticky top-10 h-fit">
                            <h2 id="final-lab-label" class="text-xl font-black italic border-b pb-6 mb-10 text-slate-800">Científico: Resultado Lab</h2>
                             <div class="grid grid-cols-3 gap-6 mb-12">
                                <div class="bg-slate-50 p-6 rounded-[2.2rem] text-center shadow-inner"><p class="text-[9px] font-bold text-slate-400 block mb-2 uppercase italic tracking-tighter">Temperatura Basal</p><p id="res-temp" class="text-4xl font-black font-mono">--</p></div>
                                <div class="bg-green-50/50 p-6 rounded-[2.2rem] border border-green-200 text-center shadow-inner"><p class="text-[10px] font-black text-green-700 block mb-2 uppercase tracking-tighter">Ajuste R²</p><p id="res-prec" class="text-4xl font-black font-mono text-green-700">--</p></div>
                                <div class="bg-slate-50 p-6 rounded-[2.2rem] text-center shadow-inner"><p class="text-[9px] font-bold text-slate-300 italic uppercase mb-2">QME Residual</p><p id="res-err" class="text-[14px] font-bold font-mono">--</p></div>
                             </div>
                             
                             <div class="space-y-10 mb-10">
                                <div id="gr-qme" class="h-64 border rounded-[2rem] p-4 bg-white shadow-inner"></div>
                                <div id="gr-reg" class="h-64 border rounded-[2rem] p-4 bg-white shadow-inner"></div>
                             </div>

                             <div class="border-2 border-slate-100 rounded-[2.2rem] overflow-hidden mb-8">
                                <p class="bg-slate-50 p-3 text-[10px] font-black uppercase text-slate-500 italic ml-4">Pré-visualização do Dataset Consolidado</p>
                                <div id="p-prev" class="max-h-56 overflow-auto text-[9px] font-mono p-1 bg-white border-t"></div>
                             </div>

                             <div class="p-8 bg-amber-50 rounded-[3.5rem] border border-amber-200 border-dotted text-center shadow-inner">
                                <button onclick="baixarDocXlsx()" class="w-full bg-yellow-500 hover:bg-yellow-600 text-white font-black py-5 rounded-full text-lg shadow-xl shadow-yellow-100 flex items-center justify-center transition-all transform active:scale-95 italic uppercase"><i class="fas fa-file-export mr-4 text-2xl"></i>Baixar Relatório Excel (.XLSX)</button>
                             </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <script>
            const U_EP = "SET_U"; const K_EP = "SET_K"; const ADMIN_ID = "abielgm@icloud.com";
            const _sb = supabase.createClient(U_EP, K_EP);
            let uiM = 'f'; let b64out = null;

            function clearLabTable() { document.getElementById('grid-lab-body').innerHTML = ''; addLabRow(15); }
            function addLabRow(n) {
                const b = document.getElementById('grid-lab-body');
                for(let i=0;i<n;i++) {
                    const r = document.createElement('tr'); r.className = 'border-b hover:bg-slate-50 transition';
                    r.innerHTML = '<td><input type="text" class="lab-input c-d"></td><td><input type="text" class="lab-input c-mi"></td><td><input type="text" class="lab-input c-ma"></td><td><input type="text" class="lab-input c-nf" placeholder="..."></td>';
                    b.appendChild(r);
                }
            }
            addLabRow(20);

            // LOGICA COLAGEM MULTI-FONTE
            document.addEventListener('paste', e => {
                if(e.target.classList.contains('lab-input')) {
                    e.preventDefault();
                    const clipText = e.clipboardData.getData('text');
                    const clipRows = clipText.split(/\\r?\\n/);
                    let focusRow = e.target.closest('tr');
                    clipRows.forEach(txtLine => {
                        if(txtLine.trim()==='') return;
                        const datArr = txtLine.split('\\t'), insIpt = focusRow.querySelectorAll('input');
                        for(let i=0; i<Math.min(4, datArr.length, insIpt.length); i++){
                            insIpt[i].value = datArr[i].trim().replace(',', '.'); 
                        }
                        focusRow = focusRow.nextElementSibling; if(!focusRow){ addLabRow(1); focusRow = document.getElementById('grid-lab-body').lastElementChild; }
                    });
                }
            });

            async function authLog() {
                const em = document.getElementById('email').value, pw = document.getElementById('password').value;
                document.getElementById('loading').classList.remove('hidden');
                let r = await _sb.auth.signInWithPassword({email:em, password:pw});
                if(r.error) { alert("Autenticação Rejeitada: " + r.error.message); document.getElementById('loading').classList.add('hidden'); }
                else location.reload();
            }

            async function labSession() {
                const {data:{user}} = await _sb.auth.getUser();
                if(user) {
                    document.getElementById('login-sec').classList.add('hidden');
                    document.getElementById('main-lab').classList.remove('hidden');
                    document.getElementById('u-user').innerText = user.email.toUpperCase();
                }
            }
            labSession();
            async function labExit() { await _sb.auth.signOut(); localStorage.clear(); window.location.replace('/'); }
            function tab(m) { uiM = m; document.getElementById('b-f').classList.toggle('bg-white', m=='f'); document.getElementById('b-m').classList.toggle('bg-white', m=='m'); document.getElementById('ui-f').classList.toggle('hidden', m=='m'); document.getElementById('ui-m').classList.toggle('hidden', m=='f'); }

            async function startAnalyticProcess() {
                document.getElementById('loading').classList.remove('hidden');
                const fd = new FormData();
                fd.append('label_agro', document.getElementById('a_nome').value || 'Projeto_Anita_Investigacao');
                fd.append('u_min', document.getElementById('v-min').value);
                fd.append('u_max', document.getElementById('v-max').value);
                fd.append('u_step', document.getElementById('v-step').value);

                if(uiM === 'f') {
                    const fI = document.getElementById('f-in');
                    if(!fI.files[0]){ alert("Nenhum arquivo para processar."); document.getElementById('loading').classList.add('hidden'); return; }
                    fd.append('file', fI.files[0]);
                } else {
                    let dOutArr = [];
                    document.querySelectorAll('#grid-lab-body tr').forEach(tr => {
                        const cellVals = Array.from(tr.querySelectorAll('input')).map(i => i.value.trim().replace(',', '.'));
                        if(cellVals[0] && cellVals[1] && cellVals[2]) {
                            if(!cellVals[3]) cellVals[3] = 'nan'; dOutArr.push(cellVals.join(';'));
                        }
                    });
                    if(dOutArr.length < 5) { alert("Grade de dados incompleta."); document.getElementById('loading').classList.add('hidden'); return; }
                    fd.append('raw_pasted', dOutArr.join('\\n'));
                }

                try {
                    const resp = await fetch('/v2/academic/process_model', {method:'POST', body:fd});
                    const dRes = await resp.json();
                    if(dRes.detail) throw new Error(dRes.detail);

                    b64out = dRes.xlsx;
                    document.getElementById('results-sec').classList.remove('hidden');
                    document.getElementById('res-temp').innerText = dRes.calc.t + "°";
                    document.getElementById('res-prec').innerText = dRes.calc.r.toFixed(4);
                    document.getElementById('res-err').innerText = dRes.calc.q.toFixed(9);
                    document.getElementById('final-lab-label').innerText = "🔬 Result Index: " + dRes.identificacao;

                    Plotly.newPlot('gr-qme', [{x: dRes.plots.qx, y: dRes.plots.qy, mode: 'lines+markers', line:{color:'black'}, marker:{size:5}}], {title:'Mínimo Residual QME (Precisão)', font:{size:10}});
                    Plotly.newPlot('gr-reg', [{x: dRes.plots.rx, y: dRes.plots.ry, mode:'markers', marker:{color:'gray', symbol:'circle-open'}, name:'Data'},{x: dRes.plots.rx, y: dRes.plots.rp, mode:'lines', line:{color:'black', dash:'dot'}, name:'Modelo'}], {title:'Reta de Regressão NF vs Soma Térmica', font:{size:10}, showlegend:false});

                    let pHtml = '<table class="w-full text-left font-mono border-collapse"><thead class="bg-slate-100 border-b"><tr><th class="p-2 border-r uppercase">Dia</th><th class="p-2 border-r text-center">TMin</th><th class="p-2 border-r text-center">TMax</th><th class="p-2 text-center text-green-700 italic">Variável</th></tr></thead><tbody>';
                    dRes.sample_view.forEach(rObj => { 
                        pHtml += `<tr class="border-b"><td class="p-2 border-r uppercase">${rObj.Data}</td><td class="p-2 border-r text-center font-bold">${rObj.Tmin}</td><td class="p-2 border-r text-center font-bold">${rObj.Tmax}</td><td class="p-2 text-center text-green-800 font-bold italic">${rObj.NF}</td></tr>`; 
                    });
                    document.getElementById('p-prev').innerHTML = pHtml + '</tbody></table>';

                    window.scrollTo({top: document.body.scrollHeight, behavior:'smooth'});
                } catch(e) {
                    alert("PROCESS_ERROR: Falha de regressão científica. Motivo:\\n" + e.message);
                } finally { document.getElementById('loading').classList.add('hidden'); }
            }

            function baixarDocXlsx() {
                if(!b64out) return alert("Planilha acadêmica não gerada.");
                const binS = atob(b64out), bBuff = new ArrayBuffer(binS.length), u8A = new Uint8Array(bBuff);
                for (let i = 0; i < binS.length; i++) u8A[i] = binS.charCodeAt(i);
                const bL = new Blob([bBuff], {type:'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'});
                const linkU = document.createElement('a'); linkU.href = window.URL.createObjectURL(bL);
                linkU.download = `Investigacao_EstimaTB_${new Date().getTime()}.xlsx`; linkU.click();
            }
        </script>
    </body>
    </html>
    """.replace("SET_U", SURL).replace("SET_K", SKEY)
    return html

# =========================================================================
# ⚙️ BLOCO 4: MOTOR ANALÍTICO - PROCESSAMENTO CIENTÍFICO (FIXED)
# =========================================================================
@app.post("/v2/academic/process_model")
async def run_agro_engine_fixed(
    file: UploadFile = None, raw_pasted: str = Form(None), label_agro: str = Form(""),
    u_min: float = Form(0.0), u_max: float = Form(20.0), u_step: float = Form(0.5)
):
    try:
        # Load com suporte total a formatos brasileiros
        if file:
            content = await file.read()
            df = pd.read_csv(BytesIO(content), sep=None, engine='python', decimal=',') if file.filename.endswith('.csv') else pd.read_excel(BytesIO(content))
        else:
            # Protege a vírgula do número enviando o dataset manual com ponto e vírgula
            df = pd.read_csv(StringIO(raw_pasted), sep=';', names=['Data','Tmin','Tmax','NF'], header=None)

        # Higiene de Colunas e Tipos (Proteção Radical)
        df.rename(columns=lambda x: 'Data' if fix_sc(x) == 'data' else x, inplace=True)
        df.rename(columns=lambda x: 'Tmin' if fix_sc(x) in ['tmin','tmín','tminima'] else x, inplace=True)
        df.rename(columns=lambda x: 'Tmax' if fix_sc(x) in ['tmax','tmáx','tmaxima'] else x, inplace=True)
        df.rename(columns=lambda x: 'NF' if fix_sc(x) in ['nf','variavel','variável'] else x, inplace=True)

        for col in ['Tmin','Tmax','NF']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', '.').str.replace('[^0-9\\.\\-]', '', regex=True), errors='coerce')
        
        # Date Engine Adaptativo
        df['Data'] = pd.to_datetime(df['Data'], dayfirst=True, errors='coerce')
        df = df.dropna(subset=['Data','Tmin','Tmax']).sort_values('Data').reset_index(drop=True)

        # Phenology filter
        val_points = df.dropna(subset=['NF'])
        if len(val_points) < 3:
            raise ValueError(f"Foram localizados apenas {len(val_points)} medições válidas da variável (NF). São necessários no mínimo 3 pontos para análise linear.")

        # Logic Matrix calculation
        df['Tmed'] = (df['Tmin'] + df['Tmax']) / 2
        p_idx = val_points.index
        results_list = []
        winner = None
        m_qme = float('inf')

        for tb_i in np.arange(u_min, u_max + u_step, u_step):
            tb_i = round(float(tb_i), 2)
            # Soma Térmica Acumulada contínua (estatisticamente precisa)
            sta_curr = (df['Tmed'] - tb_i).clip(lower=0).cumsum()
            
            X_m = sta_curr.loc[p_idx].values.reshape(-1, 1)
            y_m = df.loc[p_idx, 'NF'].values
            
            model = LinearRegression().fit(X_m, y_m)
            err = mean_squared_error(y_m, model.predict(X_m))
            score_r2 = model.score(X_m, y_m)
            results_list.append({'Tb': tb_i, 'R2': score_r2, 'QME': err})
            
            if err < m_qme:
                m_qme = err
                winner = {
                    't': tb_i, 'r': score_r2, 'q': err, 'a': model.coef_[0], 'b': model.intercept_,
                    'plt_x': sta_curr.loc[p_idx].tolist(), 'all_s': sta_curr.tolist()
                }

        err_hist = pd.DataFrame(results_list)
        
        # Reports
        df_weather_rep = df[['Data','Tmin','Tmax','Tmed']].copy()
        df_weather_rep['SomaTermica_Calculada'] = winner['all_s']
        df_reg_rep = pd.DataFrame({'Data': df.loc[p_idx, 'Data'], 'Variante_NF': df.loc[p_idx, 'NF'], 'SomaTermica_Acumulada': winner['plt_x']})

        base64_xls = export_to_xls(df_weather_rep, err_hist, df_reg_rep, winner['t'])

        return {
            "identificacao": label_agro or "Estudo de Laboratório Independente",
            "calc": {"t": float(winner['t']), "r": float(winner['r']), "q": float(winner['q'])},
            "plots": {
                "qx": err_hist['Tb'].tolist(), "qy": err_hist['QME'].tolist(),
                "rx": [float(val) for val in winner['plt_x']],
                "ry": val_points['NF'].astype(float).tolist(),
                "rp": [float(val * winner['a'] + winner['b']) for val in winner['plt_x']]
            },
            "sample_view": df.head(50).astype(str).to_dict(orient="records"),
            "xlsx": base64_xls
        }
    except Exception as ex:
        import traceback
        print(traceback.format_exc())
        return {"detail": str(ex)}
