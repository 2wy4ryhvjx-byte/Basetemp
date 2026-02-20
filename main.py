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
# 🔒 BLOCO 1: LOGIN E SEGURANÇA (FIXO)
# =========================================================================
SURL = "https://iuhtopexunirguxmjiey.supabase.co"
SKEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Iml1aHRvcGV4dW5pcmd1eG1qaWV5Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzE1MjIzNTcsImV4cCI6MjA4NzA5ODM1N30.EjDui9gQ5AlRaNpoVQisGUoXmK3j74gwzq9QSguxq78"
stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "")
ADM_MAIL = "abielgm@icloud.com"

# =========================================================================
# 🧬 BLOCO 2: UTILITÁRIOS CIENTÍFICOS
# =========================================================================
def fix_txt(t):
    if not isinstance(t, str): return t
    return "".join(c for c in unicodedata.normalize('NFKD', t) if not unicodedata.combining(c)).lower().strip()

def converter_base64(clima, erros, pheno, melhor_t):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        clima.to_excel(writer, sheet_name='Clima_Diario', index=False)
        pheno.to_excel(writer, sheet_name='Avaliacoes_Fenologia', index=False)
        erros.to_excel(writer, sheet_name='Tabela_QME', index=False)
        
        # Ajustes de Planilha Profissional
        wb = writer.book
        f_dt = wb.add_format({'num_format': 'dd/mm/yyyy'})
        ws = writer.sheets['Avaliacoes_Fenologia']
        ws.set_column('A:A', 12, f_dt)
        
        c = wb.add_chart({'type': 'scatter', 'subtype': 'smooth'})
        c.add_series({'name': 'QME vs Tb', 'categories': ['Tabela_QME', 1, 0, len(erros), 0], 'values': ['Tabela_QME', 1, 2, len(erros), 2]})
        writer.sheets['Tabela_QME'].insert_chart('E2', c)
        
    return base64.b64encode(output.getvalue()).decode()

# =========================================================================
# 🎨 BLOCO 3: INTERFACE DO SISTEMA
# =========================================================================
@app.get("/", response_class=HTMLResponse)
async def dashboard_lab():
    html_src = """
    <!DOCTYPE html>
    <html lang="pt-br">
    <head>
        <meta charset="UTF-8"><title>EstimaTB Pro 🌿</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <script src="https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2"></script>
        <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
    </head>
    <body class="bg-slate-100 font-sans min-h-screen text-slate-800">
        <div id="loading" class="hidden fixed inset-0 bg-white/95 z-50 flex flex-col items-center justify-center font-black text-green-700 italic">
            <div class="animate-spin rounded-full h-16 w-16 border-b-2 border-green-600 mb-4"></div>
            SINCRO_PROCESSAMENTO EM CURSO...
        </div>

        <div class="max-w-6xl mx-auto p-4 md:p-8">
            <div id="login-sec" class="max-w-md mx-auto bg-white p-10 rounded-[3rem] shadow-2xl mt-12 border text-center">
                <h1 class="text-4xl font-black text-green-700 italic mb-8 italic uppercase tracking-tighter decoration-yellow-400 underline decoration-4">EstimaTB🌿</h1>
                <input type="email" id="email" placeholder="E-mail" class="w-full border-2 p-4 rounded-3xl mb-4 focus:border-green-600 outline-none">
                <input type="password" id="password" placeholder="Senha" class="w-full border-2 p-4 rounded-3xl mb-6 focus:border-green-600 outline-none">
                <button onclick="logIn()" class="w-full bg-green-600 text-white py-4 rounded-3xl font-black shadow-xl">ENTRAR</button>
            </div>

            <div id="lab-sec" class="hidden">
                <div class="flex justify-between items-center bg-white p-6 rounded-[2.5rem] border mb-6 px-10 shadow-sm">
                    <p class="font-bold text-xs uppercase text-slate-400 italic">Pesquisador: <span id="u-display" class="text-green-700 not-italic"></span></p>
                    <button onclick="logOut()" class="text-red-500 font-black text-[10px] uppercase underline">Sair do Lab</button>
                </div>

                <div class="grid lg:grid-cols-12 gap-8">
                    <div class="lg:col-span-5 bg-white p-8 rounded-[3.5rem] shadow-2xl border">
                        <h3 class="font-black text-xs uppercase mb-8 border-b pb-4"><i class="fas fa-file-invoice mr-2 text-green-600"></i>Entrada Científica</h3>
                        <input type="text" id="a_nome" placeholder="Nome da Época / Variedade" class="w-full border-2 p-4 rounded-3xl mb-6 font-bold bg-slate-50 outline-none focus:border-green-500">

                        <div class="flex bg-slate-100 p-1.5 rounded-3xl mb-8">
                            <button onclick="tab('f')" id="btn-f" class="flex-1 py-3 text-[10px] font-black rounded-2xl bg-white shadow-md text-green-700">ARQUIVO ANEXO</button>
                            <button onclick="tab('m')" id="btn-m" class="flex-1 py-3 text-[10px] font-black rounded-2xl text-slate-400">PLANILHA MANUAL</button>
                        </div>

                        <div id="u-file" class="mb-10 text-center"><input type="file" id="arquivo" class="block w-full border-2 border-dashed p-10 rounded-[2.5rem] bg-slate-50 cursor-pointer"></div>

                        <div id="u-manual" class="hidden mb-10">
                            <div class="rounded-3xl border overflow-hidden mb-2 max-h-96 overflow-y-auto bg-gray-50 shadow-inner">
                                <table class="w-full border-collapse">
                                    <thead><tr><th class="th-lab">Data</th><th class="th-lab">Mín</th><th class="th-lab">Máx</th><th class="th-lab italic font-black text-green-700">Variável</th></tr></thead>
                                    <tbody id="lab-grid"></tbody>
                                </table>
                            </div>
                            <div class="flex justify-between px-2 py-2"><button onclick="add(10)" class="text-[9px] font-black text-green-600 underline uppercase tracking-tighter">+ Mais Linhas</button><button onclick="limpaGrid()" class="text-[9px] font-bold text-red-300 italic uppercase">Limpar</button></div>
                        </div>

                        <div class="bg-slate-50 p-6 rounded-[2rem] shadow-inner text-center grid grid-cols-3 gap-3 mb-10 border border-slate-100">
                            <div><label class="text-[8px] font-black mb-1 uppercase text-slate-400">Faixa Mín</label><input type="number" id="tb_m" value="0.0" class="w-full border p-2 rounded-xl text-center font-bold shadow-sm"></div>
                            <div><label class="text-[8px] font-black mb-1 uppercase text-slate-400">Faixa Máx</label><input type="number" id="tb_x" value="20.0" class="w-full border p-2 rounded-xl text-center font-bold shadow-sm"></div>
                            <div><label class="text-[8px] font-black mb-1 uppercase text-green-700 italic">Passo</label><input type="number" id="tb_s" value="0.5" step="0.1" class="w-full border border-green-200 bg-green-50 p-2 rounded-xl text-center font-bold text-green-700"></div>
                        </div>

                        <button onclick="processarLaboratorio()" id="btnCal" class="w-full bg-green-600 text-white py-6 rounded-[2.5rem] font-black text-2xl shadow-xl shadow-green-100 hover:scale-[1.03] transition-all uppercase italic">Executar Motor</button>
                    </div>

                    <div id="out-res" class="lg:col-span-7 hidden animate-in slide-in-from-bottom duration-500">
                        <div class="bg-white p-10 rounded-[4rem] shadow-2xl border-t-[14px] border-slate-900 sticky top-10">
                            <h2 class="text-2xl font-black italic tracking-tighter mb-8 border-b pb-4 text-slate-800" id="h-nome">Result Analysis</h2>
                             <div class="grid grid-cols-3 gap-4 mb-10 text-center">
                                <div class="bg-slate-50 p-6 rounded-[2rem] border shadow-inner"><p class="text-[10px] font-bold text-slate-300 italic">Temperatura Basal</p><p id="v-tb" class="text-4xl font-black font-mono">--</p></div>
                                <div class="bg-slate-50 p-6 rounded-[2rem] border border-green-50 shadow-inner"><p class="text-[10px] font-bold text-green-600">Precisão (R²)</p><p id="v-r2" class="text-4xl font-black font-mono text-green-600">--</p></div>
                                <div class="bg-slate-50 p-6 rounded-[2rem] border shadow-inner"><p class="text-[10px] font-bold text-slate-300 italic uppercase">Min QME</p><p id="v-qme" class="text-[11px] font-black font-mono">--</p></div>
                             </div>
                             
                             <div class="space-y-6">
                                <div id="gr-1" class="h-64 border rounded-[2rem] shadow-inner bg-white overflow-hidden p-2"></div>
                                <div id="gr-2" class="h-64 border rounded-[2rem] shadow-inner bg-white overflow-hidden p-2"></div>
                             </div>

                             <div id="box-xls" class="mt-8 bg-amber-50 p-6 rounded-[2rem] border-2 border-dotted border-amber-200 text-center">
                                <button onclick="baixarResult()" class="bg-amber-500 hover:bg-amber-600 text-white font-black px-10 py-4 rounded-full text-lg shadow-xl flex items-center justify-center mx-auto tracking-widest transition-all"><i class="fas fa-file-export mr-3"></i>EXPORTAR PARA EXCEL (.XLSX)</button>
                             </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <script>
            const U_S = "URL_EP"; const K_S = "KEY_EP"; const ADM = "abielgm@icloud.com";
            const _lab = supabase.createClient(U_S, K_S);
            let ui_m = 'f'; let excelB64 = null;

            function limpaGrid() { document.getElementById('lab-grid').innerHTML = ''; add(25); }
            function add(n) {
                const body = document.getElementById('lab-grid');
                for(let i=0; i<n; i++) {
                    const r = document.createElement('tr');
                    r.innerHTML = '<td><input type="text" class="sheet-cell sheet-in"></td><td><input type="text" class="sheet-cell sheet-in"></td><td><input type="text" class="sheet-cell sheet-in"></td><td><input type="text" class="sheet-cell sheet-in" placeholder="..."></td>';
                    r.className = 'border-b'; body.appendChild(r);
                }
            }
            add(20);

            // LOGICA COLAR EXCEL ROBUSTA
            document.addEventListener('paste', e => {
                if(e.target.classList.contains('sheet-in')) {
                    e.preventDefault();
                    const rawText = e.clipboardData.getData('text');
                    const rowsArr = rawText.split(/\\r?\\n/);
                    let targetRow = e.target.closest('tr');
                    
                    rowsArr.forEach(rowTxt => {
                        if(rowTxt.trim()==='') return;
                        const data = rowTxt.split('\\t'), inputs = targetRow.querySelectorAll('input');
                        for(let i=0; i<Math.min(4, data.length, inputs.length); i++) {
                            inputs[i].value = data[i].trim().replace(',', '.');
                        }
                        targetRow = targetRow.nextElementSibling;
                        if(!targetRow) { add(1); targetRow = document.getElementById('lab-grid').lastElementChild; }
                    });
                }
            });

            async function logIn() {
                const em = document.getElementById('email').value, pw = document.getElementById('password').value;
                document.getElementById('loading').classList.remove('hidden');
                let {data, error} = await _lab.auth.signInWithPassword({email:em, password:pw});
                if(error) { alert("Acesso negado: " + error.message); document.getElementById('loading').classList.add('hidden'); }
                else location.reload();
            }

            async function sessao() {
                const {data:{user}} = await _lab.auth.getUser();
                if(user) {
                    document.getElementById('login-sec').classList.add('hidden');
                    document.getElementById('lab-sec').classList.remove('hidden');
                    document.getElementById('u-display').innerText = user.email.toLowerCase();
                }
            }
            sessao();
            async function logOut() { await _lab.auth.signOut(); localStorage.clear(); window.location.replace('/'); }
            function tab(m) { ui_m = m; document.getElementById('btn-f').classList.toggle('bg-white', m=='f'); document.getElementById('btn-m').classList.toggle('bg-white', m=='m'); document.getElementById('u-file').classList.toggle('hidden', m=='m'); document.getElementById('u-manual').classList.toggle('hidden', m=='f'); }

            async function processarLaboratorio() {
                document.getElementById('loading').classList.remove('hidden');
                const form = new FormData();
                form.append('analise_id', document.getElementById('a_nome').value || 'Nova Anita Study');
                form.append('tb_min', document.getElementById('tb_m').value);
                form.append('tb_max', document.getElementById('tb_x').value);
                form.append('tb_step', document.getElementById('tb_s').value);

                if(ui_m === 'f') {
                    const fi = document.getElementById('arquivo');
                    if(!fi.files[0]) { alert("Importe seu dataset científico."); document.getElementById('loading').classList.add('hidden'); return; }
                    form.append('file', fi.files[0]);
                } else {
                    let dStr = [];
                    document.querySelectorAll('#lab-grid tr').forEach(tr => {
                        const cellVals = Array.from(tr.querySelectorAll('input')).map(i => i.value.trim());
                        if(cellVals[0] && cellVals[1] && cellVals[2]) {
                            if(!cellVals[3]) cellVals[3] = 'nan';
                            dStr.push(cellVals.join(','));
                        }
                    });
                    if(dStr.length < 5) { alert("Massa de dados insuficiente para regressão."); document.getElementById('loading').classList.add('hidden'); return; }
                    form.append('raw_m', dStr.join('\\n'));
                }

                try {
                    const response = await fetch('/v2/engine/vfinal', {method:'POST', body:form});
                    const d = await response.json();
                    if(d.detail) throw new Error(d.detail);

                    excelB64 = d.report_b64;
                    document.getElementById('out-res').classList.remove('hidden');
                    document.getElementById('v-tb').innerText = d.best.tb + "°";
                    document.getElementById('v-r2').innerText = d.best.r2.toFixed(4);
                    document.getElementById('v-qme').innerText = d.best.qme.toFixed(9);
                    document.getElementById('h-nome').innerText = "🔬 Result: " + (d.label || "Study Output");

                    Plotly.newPlot('gr-1', [{x:d.chart.q_x, y:d.chart.q_y, mode:'lines+markers', line:{color:'black'}}], {title:'Mínimo Residual (Analítico)', font:{size:10}});
                    Plotly.newPlot('gr-2', [{x:d.chart.r_x, y:d.chart.r_y, mode:'markers', marker:{color:'gray'}, name:'Data'},{x:d.chart.r_x, y:d.chart.r_p, mode:'lines', line:{color:'black', dash:'dot'}}], {title:'Modelo: NF Observado vs Soma Térmica', font:{size:10}, showlegend:false});
                    window.scrollTo({top: 0, behavior:'smooth'});
                } catch(e) {
                    alert("ALERTA CIENTÍFICO: Falha interna no motor de regressão.\\nDetalhamento: " + e.message);
                } finally { document.getElementById('loading').classList.add('hidden'); }
            }

            function baixarResult() {
                if(!excelB64) return;
                const bS = atob(excelB64), bA = new ArrayBuffer(bS.length), u8 = new Uint8Array(bA);
                for (let i = 0; i < bS.length; i++) u8[i] = bS.charCodeAt(i);
                const bl = new Blob([bA], {type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'});
                const lnk = document.createElement('a'); lnk.href = window.URL.createObjectURL(bl);
                lnk.download = `Export_EstimaTB_${new Date().getTime()}.xlsx`; lnk.click();
            }
        </script>
        <style>.sheet-cell { width: 100%; border: 1px solid #f1f5f9; padding: 4px; text-align: center; outline: none; font-size: 11px; font-family: monospace; }</style>
    </body>
    </html>
    """.replace("URL_EP", SURL).replace("KEY_EP", SKEY)
    return html_src

# =========================================================================
# ⚙️ BLOCO 4: BACKEND ENGINE - UNIFICADO
# =========================================================================
@app.post("/v2/engine/vfinal")
async def run_calculations(
    file: UploadFile = None, raw_m: str = Form(None), analise_id: str = Form(""),
    tb_min: float = Form(0.0), tb_max: float = Form(20.0), tb_step: float = Form(0.5)
):
    try:
        # Load
        if file:
            content = await file.read()
            df = pd.read_csv(BytesIO(content), sep=None, engine='python', decimal=',') if file.filename.endswith('.csv') else pd.read_excel(BytesIO(content))
        else:
            df = pd.read_csv(StringIO(raw_m), names=['Data','Tmin','Tmax','NF'], header=None)

        # Higiene de Dados Padrão EstimaTB
        df.rename(columns=lambda x: 'Data' if fix_txt(x) == 'data' else x, inplace=True)
        df.rename(columns=lambda x: 'Tmin' if fix_txt(x) in ['tmin','tmín'] else x, inplace=True)
        df.rename(columns=lambda x: 'Tmax' if fix_txt(x) in ['tmax','tmáx'] else x, inplace=True)
        df.rename(columns=lambda x: 'NF' if fix_txt(x) in ['nf','variavel','variável'] else x, inplace=True)

        for col in ['Tmin','Tmax','NF']:
            df[col] = pd.to_numeric(df[col].astype(str).str.replace(',','.').replace('nan',np.nan), errors='coerce')
        
        df['Data'] = pd.to_datetime(df['Data'], dayfirst=True, errors='coerce')
        df = df.dropna(subset=['Data','Tmin','Tmax']).sort_values('Data').reset_index(drop=True)

        valid_pheno = df.dropna(subset=['NF'])
        p_idx = valid_pheno.index
        
        if len(p_idx) < 3:
            raise ValueError("Não foi possível detectar ao menos 3 datas de avaliações fenológicas.")

        df['Tmed'] = (df['Tmin'] + df['Tmax']) / 2
        metrics = []
        best_full_sta = None
        min_err = float('inf')
        campeao_dados = {}

        t_search = np.arange(tb_min, tb_max + tb_step, tb_step)
        
        for tb in t_search:
            tb = round(float(tb), 2)
            sta_cum = (df['Tmed'] - tb).clip(lower=0).cumsum()
            
            # Regressão apenas nos pontos amostrados
            X = sta_cum.loc[p_idx].values.reshape(-1, 1)
            y = df.loc[p_idx, 'NF'].values
            
            lr = LinearRegression().fit(X, y)
            preds = lr.predict(X)
            qme = mean_squared_error(y, preds)
            r2 = lr.score(X,y)
            
            metrics.append({'Tb': tb, 'R2': r2, 'QME': qme})
            
            if qme < min_err:
                min_err = qme
                campeao_dados = {
                    'tb': tb, 'r2': r2, 'qme': qme, 'a': lr.coef_[0], 'b': lr.intercept_,
                    'x_plot': sta_cum.loc[p_idx].tolist(),
                    'full_sta': sta_cum.tolist()
                }

        m_df = pd.DataFrame(metrics)
        # Construção da exportação (igual ao streamlit original)
        rep_meteor = df[['Data','Tmin','Tmax','Tmed']].copy()
        rep_meteor['STa_Final'] = campeao_dados['full_sta']
        
        rep_reg = pd.DataFrame({
            'Data': df.loc[p_idx, 'Data'],
            'Variável (Obs)': df.loc[p_idx, 'NF'],
            'STa_Acumulada': campeao_dados['x_plot']
        })

        xls_b64 = converter_base64(rep_meteor, m_df, rep_reg, campeao_dados['tb'])

        return {
            "label": analise_id,
            "best": {"tb": campeao_dados['tb'], "r2": campeao_dados['r2'], "qme": campeao_dados['qme']},
            "chart": {
                "q_x": m_df['Tb'].tolist(), "q_y": m_df['QME'].tolist(),
                "r_x": campeao_dados['x_plot'], "r_y": df.loc[p_idx, 'NF'].tolist(),
                "r_p": [float(x * campeao_dados['a'] + campeao_dados['b']) for x in campeao_dados['x_plot']]
            },
            "report_b64": xls_xls_b64 if 'xls_b64' in locals() else xls_b64
        }
    except Exception as e:
        import traceback
        print(traceback.format_exc())
        return {"detail": str(e)}
