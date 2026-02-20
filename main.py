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
# 🧬 BLOCO 2: MOTOR CIENTÍFICO E EXCEL
# =========================================================================
def fix_scientific_txt(t):
    if not isinstance(t, str): return t
    return "".join(c for c in unicodedata.normalize('NFKD', t) if not unicodedata.combining(c)).lower().strip()

def build_excel_output(clima, erros, pheno, tb_final):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        clima.to_excel(writer, sheet_name='Base_Dados_Diarios', index=False)
        pheno.to_excel(writer, sheet_name='Resultados_NF_vs_STa', index=False)
        erros.to_excel(writer, sheet_name='Analise_Residual_QME', index=False)
        wb = writer.book
        f_dt = wb.add_format({'num_format': 'dd/mm/yyyy'})
        if 'Resultados_NF_vs_STa' in writer.sheets:
            writer.sheets['Resultados_NF_vs_STa'].set_column('A:A', 12, f_dt)
        chart = wb.add_chart({'type': 'scatter', 'subtype': 'smooth'})
        chart.add_series({'name': 'QME vs Tb', 'categories': ['Analise_Residual_QME', 1, 0, len(erros), 0], 'values': ['Analise_Residual_QME', 1, 2, len(erros), 2]})
        writer.sheets['Analise_Residual_QME'].insert_chart('E2', chart)
    return base64.b64encode(output.getvalue()).decode()

# =========================================================================
# 🎨 BLOCO 3: INTERFACE PROFISSIONAL
# =========================================================================
@app.get("/", response_class=HTMLResponse)
async def laboratory_portal():
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
    <body class="bg-slate-50 font-sans min-h-screen text-slate-800">
        <div id="loader" class="hidden fixed inset-0 bg-white/95 z-50 flex flex-col items-center justify-center font-black text-green-700 italic">
            <div class="animate-spin rounded-full h-16 w-16 border-b-2 border-green-600 mb-4"></div>
            MOTOR CIENTÍFICO EM PROCESSAMENTO...
        </div>

        <div class="max-w-6xl mx-auto p-4 md:p-10">
            <div id="login-sec" class="max-w-md mx-auto bg-white p-12 rounded-[3rem] shadow-2xl mt-12 border text-center">
                <h1 class="text-4xl font-black text-green-700 italic mb-8 italic uppercase tracking-tighter decoration-yellow-400 underline decoration-4">EstimaTB🌿</h1>
                <input type="email" id="email" placeholder="E-mail Acadêmico" class="w-full border-2 p-4 rounded-3xl mb-4 focus:border-green-600 outline-none bg-slate-50">
                <input type="password" id="password" placeholder="Senha" class="w-full border-2 p-4 rounded-3xl mb-6 focus:border-green-600 outline-none bg-slate-50">
                <button onclick="fazerLogin()" class="w-full bg-green-600 text-white py-4 rounded-3xl font-black shadow-xl hover:bg-green-700">ENTRAR NO SISTEMA</button>
                <button onclick="toggleRegister()" id="sw-btn" class="text-green-600 font-bold text-[9px] uppercase mt-6 block mx-auto">Solicitar Novo Acesso</button>
            </div>

            <div id="main-lab" class="hidden">
                <div class="flex flex-col md:flex-row justify-between items-center bg-white p-6 rounded-[2.5rem] border mb-8 px-10 shadow-sm border-slate-200">
                    <p class="font-bold text-[10px] uppercase text-slate-400 italic italic">Responsável Técnico: <span id="u-display" class="text-green-700 not-italic font-black text-sm"></span></p>
                    <button onclick="fazerLogout()" class="text-red-500 font-black text-[10px] uppercase border border-red-100 px-6 py-1.5 rounded-full hover:bg-red-50">Sair do Sistema</button>
                </div>

                <div class="grid lg:grid-cols-12 gap-8">
                    <div class="lg:col-span-5 space-y-6">
                        <div class="bg-white p-8 rounded-[3.5rem] shadow-xl border">
                            <h3 class="font-black text-[10px] uppercase mb-10 border-b pb-4 italic"><i class="fas fa-microscope mr-2 text-green-600"></i>Gestão de Entrada de Dados</h3>
                            
                            <input type="text" id="input_label" placeholder="Nome da Análise (Opcional)" class="w-full border-2 p-4 rounded-3xl mb-8 font-bold bg-slate-50 outline-none focus:border-green-500 text-sm">

                            <div class="flex bg-slate-100 p-1.5 rounded-3xl mb-8 border border-slate-200 shadow-inner">
                                <button onclick="tab('f')" id="b-f" class="flex-1 py-3 text-[10px] font-black rounded-2xl bg-white shadow-md text-green-700 uppercase italic">Anexar Arquivo</button>
                                <button onclick="tab('m')" id="b-m" class="flex-1 py-3 text-[10px] font-black rounded-2xl text-slate-400 uppercase tracking-tighter">Digitação Direta</button>
                            </div>

                            <div id="box-f"><input type="file" id="f_input" class="block w-full border-2 border-dashed p-10 rounded-[2.5rem] bg-slate-50 cursor-pointer text-[10px]"></div>

                            <div id="box-m" class="hidden">
                                <p class="text-[9px] font-bold text-slate-400 uppercase mb-4 italic text-center underline decoration-slate-100">Cole seu conteúdo do Excel na grade abaixo</p>
                                <div class="rounded-3xl border overflow-hidden mb-2 max-h-96 overflow-y-auto bg-gray-50 shadow-inner border-slate-200">
                                    <table class="w-full border-collapse">
                                        <thead class="sticky top-0 z-10 shadow-sm"><tr><th class="p-3 text-[9px] bg-slate-100 border font-black uppercase text-slate-500">Data</th><th class="p-3 text-[9px] bg-slate-100 border font-black uppercase text-slate-500">Tmin</th><th class="p-3 text-[9px] bg-slate-100 border font-black uppercase text-slate-500">Tmax</th><th class="p-3 text-[9px] bg-slate-100 border font-black uppercase text-green-700">NF</th></tr></thead>
                                        <tbody id="manual-grid"></tbody>
                                    </table>
                                </div>
                                <div class="flex justify-between px-2 mb-4">
                                    <button onclick="add(10)" class="text-[9px] font-bold text-green-600 uppercase underline">+ Adicionar Linhas</button>
                                    <button onclick="limpa()" class="text-[9px] font-bold text-red-400 uppercase italic">Limpar Tudo</button>
                                </div>
                            </div>

                            <div class="bg-slate-50 p-8 rounded-[2.5rem] shadow-inner text-center grid grid-cols-3 gap-3 mb-10 border border-slate-100">
                                <div class="flex flex-col"><label class="text-[8px] font-black uppercase text-slate-400">Tb Mín</label><input type="number" id="v-min" value="0.0" class="w-full border p-2 rounded-xl text-center font-black"></div>
                                <div class="flex flex-col"><label class="text-[8px] font-black uppercase text-slate-400">Tb Máx</label><input type="number" id="v-max" value="20.0" class="w-full border p-2 rounded-xl text-center font-black"></div>
                                <div class="flex flex-col"><label class="text-[8px] font-black uppercase text-green-700">Passo</label><input type="number" id="v-step" value="0.5" step="0.1" class="w-full border-2 border-green-200 bg-white p-2 rounded-xl text-center font-black text-green-700"></div>
                            </div>

                            <button onclick="gerarModelagem()" class="w-full bg-green-600 text-white py-6 rounded-[2.5rem] font-black text-xl shadow-xl hover:bg-green-700 transform active:scale-95 transition-all tracking-widest italic uppercase">Executar Modelagem</button>
                        </div>
                    </div>

                    <!-- Side Display -->
                    <div id="side-out" class="lg:col-span-7 hidden animate-in slide-in-from-right duration-500">
                        <div class="bg-white p-10 rounded-[3.5rem] shadow-2xl border-t-[14px] border-slate-900 sticky top-10 h-fit">
                            <div class="grid grid-cols-3 gap-6 mb-12 text-center">
                                <div class="bg-slate-50 p-6 rounded-[2rem] border shadow-inner"><p class="text-[10px] font-bold text-slate-300 uppercase italic">Temp. Basal</p><p id="o-tb" class="text-4xl font-black font-mono">--</p></div>
                                <div class="bg-green-50/50 p-6 rounded-[2rem] border-2 border-green-100 shadow-inner"><p class="text-[10px] font-black text-green-600 uppercase italic">Precisão R²</p><p id="o-r2" class="text-4xl font-black font-mono text-green-600">--</p></div>
                                <div class="bg-slate-50 p-6 rounded-[2rem] border shadow-inner"><p class="text-[10px] font-bold text-slate-300 uppercase italic">QME</p><p id="o-qme" class="text-[12px] font-black font-mono tracking-tighter">--</p></div>
                             </div>
                             
                             <div class="space-y-6 mb-10">
                                <div id="plt1" class="h-64 border rounded-[2rem] p-2 bg-white"></div>
                                <div id="plt2" class="h-64 border rounded-[2rem] p-2 bg-white"></div>
                             </div>

                             <div class="rounded-[2.5rem] border-2 border-slate-100 mb-8 overflow-hidden">
                                <p class="bg-slate-50 p-4 text-[9px] font-black uppercase text-slate-400 italic">Monitoramento de Base Processada</p>
                                <div id="prev-area" class="max-h-56 overflow-auto bg-white"></div>
                             </div>

                             <div id="btn-export" class="p-8 bg-amber-50/50 border-2 border-dashed border-amber-200 rounded-[2.5rem] text-center">
                                <button onclick="downloadExcel()" class="bg-amber-500 hover:bg-amber-600 text-white font-black px-12 py-5 rounded-full text-md shadow-2xl flex items-center justify-center mx-auto tracking-widest"><i class="fas fa-file-download mr-3 text-2xl"></i>BAIXAR RELATÓRIO EXCEL (.XLSX)</button>
                             </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <script>
            const UR = "EP_URL"; const KY = "EP_KEY"; const ME = "abielgm@icloud.com";
            const _lab = supabase.createClient(UR, KY);
            let uiM = 'f'; let xls64 = null;

            function limpa() { document.getElementById('manual-grid').innerHTML = ''; add(15); }
            function add(n) {
                const b = document.getElementById('manual-grid');
                for(let i=0; i<n; i++){
                    const tr = document.createElement('tr'); tr.className = 'border-b';
                    tr.innerHTML = '<td><input type="text" class="c-in s-d"></td><td><input type="text" class="c-in s-mi"></td><td><input type="text" class="c-in s-ma"></td><td><input type="text" class="c-in s-v" placeholder="..."></td>';
                    b.appendChild(tr);
                }
            }
            add(20);

            // LOGICA COLAR SEMERU: Separador de Tabulação com Ponto Decimal
            document.addEventListener('paste', e => {
                if(e.target.classList.contains('c-in')) {
                    e.preventDefault();
                    const clip = e.clipboardData.getData('text').split(/\\r?\\n/);
                    let row = e.target.closest('tr');
                    clip.forEach(t => {
                        if(!t.trim()) return;
                        const ds = t.split('\\t'), ins = row.querySelectorAll('input');
                        for(let i=0; i<Math.min(4, ds.length, ins.length); i++){
                            ins[i].value = ds[i].trim().replace(',', '.'); // Já limpa a vírgula do excel brasileiro
                        }
                        row = row.nextElementSibling; if(!row){ add(1); row = document.getElementById('manual-grid').lastElementChild; }
                    });
                }
            });

            async function fazerLogin() {
                const e = document.getElementById('email').value, p = document.getElementById('password').value;
                document.getElementById('loader').classList.remove('hidden');
                let {data, error} = await _lab.auth.signInWithPassword({email:e, password:p});
                if(error){ alert("ERRO DE ACESSO: " + error.message); document.getElementById('loader').classList.add('hidden'); }
                else location.reload();
            }
            async function logCheck() {
                const {data:{user}} = await _lab.auth.getUser();
                if(user) {
                    document.getElementById('login-sec').classList.add('hidden');
                    document.getElementById('lab-sec').classList.remove('hidden');
                    document.getElementById('u-display').innerText = user.email;
                }
            }
            logCheck();
            async function fazerLogout() { await _lab.auth.signOut(); localStorage.clear(); window.location.replace('/'); }
            function tab(m) { uiM = m; document.getElementById('b-f').classList.toggle('bg-white', m=='f'); document.getElementById('b-m').classList.toggle('bg-white', m=='m'); document.getElementById('box-f').classList.toggle('hidden', m=='m'); document.getElementById('box-m').classList.toggle('hidden', m=='f'); }

            async function gerarModelagem() {
                document.getElementById('loader').classList.remove('hidden');
                const fd = new FormData();
                fd.append('label', document.getElementById('input_label').value || 'Exp. Agrometeorologia');
                fd.append('vmin', document.getElementById('v-min').value);
                fd.append('vmax', document.getElementById('v-max').value);
                fd.append('vstep', document.getElementById('v-step').value);

                if(uiM === 'f') {
                    const fi = document.getElementById('f_input');
                    if(!fi.files[0]){ alert("Anexe sua planilha de pesquisa!"); document.getElementById('loader').classList.add('hidden'); return; }
                    fd.append('file', fi.files[0]);
                } else {
                    let dArr = [];
                    document.querySelectorAll('#manual-grid tr').forEach(tr => {
                        // Enviamos com ponto e vírgula para não chocar com a vírgula dos decimais brasileiros no read_csv
                        const cells = Array.from(tr.querySelectorAll('input')).map(i => i.value.trim().replace(',', '.'));
                        if(cells[0] && cells[1] && cells[2]) { if(!cells[3]) cells[3] = 'nan'; dArr.push(cells.join(';')); }
                    });
                    if(dArr.length < 5) { alert("Base manual com dados insuficientes."); document.getElementById('loader').classList.add('hidden'); return; }
                    fd.append('manual', dArr.join('\\n'));
                }

                try {
                    const resp = await fetch('/api/lab/process', {method:'POST', body:fd});
                    const d = await resp.json();
                    if(d.detail) throw new Error(d.detail);

                    xls64 = d.xls;
                    document.getElementById('side-out').classList.remove('hidden');
                    document.getElementById('o-tb').innerText = d.res.temp + "°";
                    document.getElementById('o-r2').innerText = d.res.r2.toFixed(4);
                    document.getElementById('o-qme').innerText = d.res.qme.toFixed(9);
                    document.getElementById('h-lab').innerText = "🔬 Result: " + (d.nome || "Análise Térmica");

                    Plotly.newPlot('plt1', [{x: d.plt.qx, y: d.plt.qy, mode: 'lines+markers', line:{color:'black'}}], {title:'Análise Residual QME', font:{size:10}});
                    Plotly.newPlot('plt2', [{x: d.plt.rx, y: d.plt.ry, mode:'markers', marker:{color:'gray'}},{x: d.plt.rx, y: d.plt.rp, mode:'lines', line:{color:'black', dash:'dot'}}], {title:'Modelo Experimental: NF vs STa', font:{size:10}, showlegend:false});

                    let tbH = '<table class="w-full text-left text-[9px] font-mono"><thead class="bg-slate-50 border-b"><tr><th class="p-2 border-r">Data</th><th class="p-2 border-r">T.Mín</th><th class="p-2 border-r">T.Máx</th><th class="p-2">Var.</th></tr></thead><tbody>';
                    d.preview.forEach(r => { tbH += `<tr class="border-b"><td class="p-2 border-r">${r.Data}</td><td class="p-2 border-r text-center">${r.Tmin}</td><td class="p-2 border-r text-center">${r.Tmax}</td><td class="p-2 text-center text-green-700 font-bold">${r.NF}</td></tr>`; });
                    document.getElementById('prev-area').innerHTML = tbH + '</tbody></table>';

                    window.scrollTo({top: 0, behavior:'smooth'});
                } catch(e) {
                    alert("ALERTA CIENTÍFICO: Falha no Motor Acadêmico.\\n" + e.message);
                } finally { document.getElementById('loader').classList.add('hidden'); }
            }

            function downloadExcel() {
                if(!xls64) return;
                const bStr = atob(xls64), bArr = new ArrayBuffer(bStr.length), uint = new Uint8Array(bArr);
                for(let i=0; i<bStr.length; i++) uint[i] = bStr.charCodeAt(i);
                const b = new Blob([bArr], {type:'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'});
                const link = document.createElement('a'); link.href = window.URL.createObjectURL(b);
                link.download = `Investigacao_Agro_EstimaTB.xlsx`; link.click();
            }
        </script>
        <style>.c-in { width:100%; border:none; padding:6px; font-size:11px; font-family:monospace; text-align:center; }</style>
    </body>
    </html>
    """.replace("EP_URL", SURL).replace("EP_KEY", SKEY)
    return html_src

# =========================================================================
# ⚙️ BLOCO 4: ENGINE - PROCESSAMENTO SEGURO
# =========================================================================
@app.post("/api/lab/process")
async def run_agro_engine(
    file: UploadFile = None, manual: str = Form(None), label: str = Form(""),
    vmin: float = Form(0.0), vmax: float = Form(20.0), vstep: float = Form(0.5)
):
    try:
        if file:
            content = await file.read()
            df = pd.read_csv(BytesIO(content), sep=None, engine='python', decimal=',') if file.filename.endswith('.csv') else pd.read_excel(BytesIO(content))
        else:
            # Semicolon separator strictly used to prevent decimal comma confusion
            df = pd.read_csv(StringIO(manual), sep=';', names=['Data','Tmin','Tmax','NF'], header=None)

        # Standardizing ColNames
        for col in df.columns:
            nc = fix_scientific_txt(col)
            if nc == 'data': df.rename(columns={col: 'Data'}, inplace=True)
            elif nc in ['tmin','tminima']: df.rename(columns={col: 'Tmin'}, inplace=True)
            elif nc in ['tmax','tmaxima']: df.rename(columns={col: 'Tmax'}, inplace=True)
            elif nc in ['nf','variavel','variável']: df.rename(columns={col: 'NF'}, inplace=True)

        # Numerical Clean (Force point decimals and filter noise)
        for c in ['Tmin','Tmax','NF']:
            df[c] = pd.to_numeric(df[c].astype(str).str.replace(',','.').str.replace('[^0-9\.\-]', '', regex=True), errors='coerce')
        
        # Adaptive Date Conversion
        df['Data'] = pd.to_datetime(df['Data'], dayfirst=True, errors='coerce')
        df = df.dropna(subset=['Data','Tmin','Tmax']).sort_values('Data').reset_index(drop=True)

        # Pheno Selection
        pheno_rows = df.dropna(subset=['NF'])
        if len(pheno_rows) < 3:
            raise ValueError(f"Foram encontradas apenas {len(pheno_rows)} medições da Variável. O motor exige pelo menos 3 avaliações fenomenológicas para correlação.")

        # Logic engine
        df['Tmed'] = (df['Tmin'] + df['Tmax']) / 2
        p_idx = pheno_rows.index
        scan = []
        winner = None
        min_qme_val = float('inf')

        t_steps = np.arange(vmin, vmax + vstep, vstep)
        for ti in t_steps:
            ti = round(float(ti), 2)
            sta_acum = (df['Tmed'] - ti).clip(lower=0).cumsum()
            
            X_fit = sta_acum.loc[p_idx].values.reshape(-1, 1)
            y_fit = df.loc[p_idx, 'NF'].values
            
            lr = LinearRegression().fit(X_fit, y_fit)
            r2_val, qme_val = lr.score(X_fit, y_fit), mean_squared_error(y_fit, lr.predict(X_fit))
            scan.append({'Tb': ti, 'R2': r2_val, 'QME': qme_val})
            
            if qme_val < min_qme_val:
                min_qme_val = qme_val
                winner = {
                    't': ti, 'r2': r2_val, 'qme': qme_val, 'a': lr.coef_[0], 'b': lr.intercept_,
                    'x_plt': sta_acum.loc[p_idx].tolist(), 'all_sta': sta_acum.tolist()
                }

        metrics_df = pd.DataFrame(scan)
        
        # Construct Excel Datasets
        clima_data = df[['Data','Tmin','Tmax','Tmed']].copy()
        clima_data['STa_Optimized'] = winner['all_sta']
        pheno_data = pd.DataFrame({'Data': df.loc[p_idx, 'Data'], 'Variante_Observada': df.loc[p_idx, 'NF'], 'STa_Acumulado': winner['x_plt']})

        # Xls export
        b64 = export_xlsx(clima_data, metrics_df, pheno_data, winner['t'])

        return {
            "nome": label, "res": {"temp": winner['t'], "r2": winner['r2'], "qme": winner['qme']},
            "plt": {"qx": metrics_df['Tb'].tolist(), "qy": metrics_df['QME'].tolist(), "rx": winner['x_plt'], "ry": pheno_rows['NF'].astype(float).tolist(), "rp": [float(val * winner['a'] + winner['b']) for val in winner['x_plt']]},
            "preview": df.head(15).astype(str).to_dict(orient="records"), "xls": b64
        }
    except Exception as e:
        import traceback
        print(traceback.format_exc())
        return {"detail": str(e)}
