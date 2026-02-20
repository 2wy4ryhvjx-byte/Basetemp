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

def export_xlsx(clima, erros, pheno, t_otima):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        clima.to_excel(writer, sheet_name='Base_Meteorologica', index=False)
        pheno.to_excel(writer, sheet_name='Regressao_NF_STa', index=False)
        erros.to_excel(writer, sheet_name='Resultados_QME', index=False)
        wb = writer.book
        f_dt = wb.add_format({'num_format': 'dd/mm/yyyy'})
        ws = writer.sheets['Regressao_NF_STa']
        ws.set_column('A:A', 12, f_dt)
        chart = wb.add_chart({'type': 'scatter', 'subtype': 'smooth'})
        chart.add_series({'name': 'QME vs Tb', 'categories': ['Resultados_QME', 1, 0, len(erros), 0], 'values': ['Resultados_QME', 1, 2, len(erros), 2]})
        writer.sheets['Resultados_QME'].insert_chart('E2', chart)
    return base64.b64encode(output.getvalue()).decode()

# =========================================================================
# 🎨 BLOCO 3: INTERFACE DO SISTEMA
# =========================================================================
@app.get("/", response_class=HTMLResponse)
async def lab_interface():
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
            .sheet-cell { width: 100%; border: 1px solid #f1f5f9; padding: 4px; text-align: center; outline: none; font-size: 11px; font-family: monospace; }
            .th-scientific { background: #f8fafc; font-size: 9px; font-weight: 900; color: #475569; padding: 12px; border: 1px solid #e2e8f0; text-transform: uppercase; }
        </style>
    </head>
    <body class="bg-slate-50 font-sans min-h-screen text-slate-800">
        <div id="loader" class="hidden fixed inset-0 bg-white/95 z-50 flex flex-col items-center justify-center font-black text-green-700 italic">
            <div class="animate-spin rounded-full h-16 w-16 border-b-2 border-green-600 mb-4"></div>
            AGRO-MOTOR EM PROCESSAMENTO...
        </div>

        <div class="max-w-6xl mx-auto p-4 md:p-10">
            <!-- TELA LOGIN -->
            <div id="login-sec" class="max-w-md mx-auto bg-white p-12 rounded-[3rem] shadow-2xl mt-12 border text-center">
                <h1 class="text-5xl font-black text-green-700 italic mb-2 tracking-tighter uppercase underline decoration-yellow-400">EstimaTB🌿</h1>
                <p class="text-[10px] font-bold text-slate-300 uppercase tracking-widest mb-10 italic">Academic Version</p>
                <div class="space-y-4">
                    <input type="email" id="email" placeholder="E-mail" class="w-full border-2 p-4 rounded-3xl outline-none focus:border-green-600 shadow-inner">
                    <input type="password" id="password" placeholder="Senha" class="w-full border-2 p-4 rounded-3xl outline-none focus:border-green-600 shadow-inner">
                    <button onclick="logIn()" class="w-full bg-green-600 text-white py-4 rounded-3xl font-black shadow-xl hover:bg-green-700 transition">ENTRAR NO SISTEMA</button>
                    <button onclick="toggleLog()" id="sw" class="text-green-600 font-bold text-[9px] uppercase mt-4">Criar Novo Registro</button>
                </div>
            </div>

            <!-- DASHBOARD LAB -->
            <div id="lab-sec" class="hidden animate-in fade-in duration-700">
                <div class="flex flex-col md:flex-row justify-between items-center bg-white p-6 rounded-[2.5rem] shadow-sm border mb-10 px-10 gap-4">
                    <p class="font-bold text-xs uppercase text-slate-400 italic">Pesquisador Logado: <span id="u-display" class="text-green-700 font-black not-italic ml-2 uppercase"></span></p>
                    <button onclick="logOut()" class="text-red-500 font-black text-[10px] uppercase border px-4 py-1.5 rounded-full border-red-50 hover:bg-red-50 transition">Sair</button>
                </div>

                <div class="grid lg:grid-cols-12 gap-8">
                    <!-- Config Side -->
                    <div class="lg:col-span-5 space-y-6">
                        <div class="bg-white p-10 rounded-[3.5rem] shadow-xl border">
                            <h3 class="font-black text-[10px] uppercase mb-10 border-b pb-4 flex items-center italic tracking-widest"><i class="fas fa-database mr-3 text-green-600"></i>Configurações de Dados</h3>
                            
                            <label class="text-[9px] font-black text-slate-400 mb-1 ml-2 block uppercase tracking-tight">Nome da Análise (Ex: Época 12 Anita)</label>
                            <input type="text" id="a_id" class="w-full border-2 p-4 rounded-3xl mb-8 font-bold bg-slate-50 outline-none focus:border-green-500 shadow-inner">

                            <div class="flex bg-slate-100 p-1.5 rounded-3xl mb-8 border border-slate-200">
                                <button onclick="tab('f')" id="btn-f" class="flex-1 py-3 text-[10px] font-black rounded-2xl bg-white shadow-md text-green-700 transition-all uppercase">Carregar Arquivo</button>
                                <button onclick="tab('m')" id="btn-m" class="flex-1 py-3 text-[10px] font-black rounded-2xl text-slate-400 transition-all uppercase italic">Digitação Direta</button>
                            </div>

                            <div id="u-file" class="mb-10 text-center"><input type="file" id="arquivo" class="block w-full border-2 border-dashed p-10 rounded-[2.5rem] bg-slate-50 cursor-pointer text-xs"></div>

                            <div id="u-manual" class="hidden mb-10">
                                <div class="rounded-3xl border overflow-hidden mb-2 max-h-96 overflow-y-auto bg-gray-50 shadow-inner">
                                    <table class="w-full border-collapse">
                                        <thead class="sticky top-0 shadow-sm"><tr><th class="th-scientific">Data</th><th class="th-scientific">Min</th><th class="th-scientific">Max</th><th class="th-scientific italic text-green-700">NF</th></tr></thead>
                                        <tbody id="lab-grid"></tbody>
                                    </table>
                                </div>
                                <div class="flex justify-between p-2"><button onclick="addRows(10)" class="text-[9px] font-black text-green-600 hover:underline uppercase">+ Adicionar Linhas</button><button onclick="limpa()" class="text-[9px] font-bold text-red-400 italic">Zerar Tabela</button></div>
                            </div>

                            <div class="bg-slate-50 p-8 rounded-[2.5rem] shadow-inner text-center grid grid-cols-3 gap-4 mb-10 border border-slate-100">
                                <div class="flex flex-col"><label class="text-[8px] font-bold uppercase text-slate-400">Tb Mín</label><input type="number" id="v_min" value="0.0" class="w-full border p-2 rounded-xl text-center font-bold"></div>
                                <div class="flex flex-col"><label class="text-[8px] font-bold uppercase text-slate-400">Tb Máx</label><input type="number" id="v_max" value="20.0" class="w-full border p-2 rounded-xl text-center font-bold"></div>
                                <div class="flex flex-col"><label class="text-[8px] font-bold text-green-700 underline uppercase">Passo</label><input type="number" id="v_step" value="0.5" step="0.1" class="w-full border border-green-100 p-2 rounded-xl text-center font-bold text-green-700 bg-white"></div>
                            </div>

                            <button onclick="executarMotor()" id="btnCal" class="w-full bg-green-600 text-white py-5 rounded-[2.5rem] font-black text-xl shadow-xl shadow-green-100 hover:scale-[1.03] transition-all uppercase tracking-widest italic">Executar Modelagem</button>
                        </div>
                    </div>

                    <!-- Metrics Side -->
                    <div id="res-sec" class="lg:col-span-7 hidden animate-in slide-in-from-right duration-700">
                        <div class="bg-white p-10 rounded-[3.5rem] shadow-2xl border-t-[16px] border-slate-900 sticky top-10 h-fit">
                             <h2 class="text-2xl font-black italic tracking-tighter mb-8 border-b pb-6" id="h-lab">Analytic Report Output</h2>
                             <div class="grid grid-cols-3 gap-6 mb-12">
                                <div class="bg-slate-50 p-6 rounded-[2rem] border shadow-inner"><p class="text-[10px] font-black text-slate-300 uppercase">Temperatura Basal</p><p id="v-tb" class="text-4xl font-black font-mono">--</p></div>
                                <div class="bg-slate-50 p-6 rounded-[2rem] border border-green-100 shadow-inner"><p class="text-[10px] font-black text-green-600 uppercase">Coef. Ajuste (R²)</p><p id="v-r2" class="text-4xl font-black font-mono text-green-600">--</p></div>
                                <div class="bg-slate-50 p-6 rounded-[2rem] border shadow-inner"><p class="text-[10px] font-black text-slate-300 italic">Mínimo QME</p><p id="v-qme" class="text-[13px] font-bold font-mono text-slate-500">--</p></div>
                             </div>
                             
                             <div class="space-y-8 mb-12">
                                <div id="gr1" class="h-64 border rounded-[2rem] bg-white p-4"></div>
                                <div id="gr2" class="h-64 border rounded-[2rem] bg-white p-4"></div>
                             </div>

                             <div class="mb-10 overflow-hidden border-2 border-slate-50 rounded-3xl">
                                <h3 class="bg-slate-100 p-4 text-[9px] font-black uppercase text-slate-500 italic tracking-widest">Base de Dados Processada pelo Motor</h3>
                                <div id="v-preview" class="max-h-60 overflow-auto bg-white"></div>
                             </div>

                             <div id="btn-export-sec" class="mt-4 p-8 bg-slate-50 rounded-[3rem] border border-dashed border-slate-200">
                                <button onclick="baixarResultados()" class="w-full bg-yellow-500 hover:bg-yellow-600 text-white font-black py-5 rounded-full text-lg shadow-xl shadow-yellow-100 flex items-center justify-center italic tracking-widest transition-all"><i class="fas fa-file-download mr-4 text-2xl"></i>BAIXAR RELATÓRIO COMPLETO (.XLSX)</button>
                             </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <script>
            const SU = "URL_VAL"; const SK = "KEY_VAL"; const ADM = "abielgm@icloud.com";
            const _supabase = supabase.createClient(SU, SK);
            let uiMode = 'f'; let excelOutput = null;

            function limpa() { document.getElementById('lab-grid').innerHTML = ''; addRows(15); }
            function addRows(n) {
                const b = document.getElementById('lab-grid');
                for(let i=0; i<n; i++) {
                    const r = document.createElement('tr'); r.className = 'border-b';
                    r.innerHTML = '<td><input type="text" class="sheet-cell s-in"></td><td><input type="text" class="sheet-cell s-in"></td><td><input type="text" class="sheet-cell s-in"></td><td><input type="text" class="sheet-cell s-in" placeholder="..."></td>';
                    b.appendChild(r);
                }
            }
            addRows(20);

            document.addEventListener('paste', e => {
                if(e.target.classList.contains('sheet-in')) {
                    e.preventDefault();
                    const clip = e.clipboardData.getData('text').split(/\\r?\\n/);
                    let rowTr = e.target.closest('tr');
                    clip.forEach(t => {
                        if(!t.trim()) return;
                        const dataArr = t.split('\\t'), ins = rowTr.querySelectorAll('input');
                        for(let i=0; i<Math.min(4, dataArr.length, ins.length); i++) {
                            ins[i].value = dataArr[i].trim().replace(',', '.');
                        }
                        rowTr = rowTr.nextElementSibling; if(!rowTr) { addRows(1); rowTr = document.getElementById('lab-grid').lastElementChild; }
                    });
                }
            });

            async function logIn() {
                const e = document.getElementById('email').value, p = document.getElementById('password').value;
                document.getElementById('loader').classList.remove('hidden');
                let {data, error} = await _supabase.auth.signInWithPassword({email:e, password:p});
                if(error) { alert("Autenticação Inválida: " + error.message); document.getElementById('loader').classList.add('hidden'); }
                else location.reload();
            }
            async function checkS() {
                const {data:{user}} = await _supabase.auth.getUser();
                if(user) {
                    document.getElementById('login-sec').classList.add('hidden');
                    document.getElementById('lab-sec').classList.remove('hidden');
                    document.getElementById('u-display').innerText = user.email.toLowerCase();
                }
            }
            checkS();
            async function logOut() { await _supabase.auth.signOut(); localStorage.clear(); window.location.replace('/'); }

            function tab(m) { uiMode = m; document.getElementById('btn-f').classList.toggle('bg-white', m=='f'); document.getElementById('btn-m').classList.toggle('bg-white', m=='m'); document.getElementById('u-file').classList.toggle('hidden', m=='m'); document.getElementById('u-manual').classList.toggle('hidden', m=='f'); }

            async function executarMotor() {
                document.getElementById('loader').classList.remove('hidden');
                const form = new FormData();
                form.append('analise_nome', document.getElementById('a_id').value || 'Projeto Científico Anita');
                form.append('min', document.getElementById('v_min').value);
                form.append('max', document.getElementById('v_max').value);
                form.append('step', document.getElementById('v_step').value);

                if(uiMode === 'f') {
                    const fi = document.getElementById('arquivo');
                    if(!fi.files[0]) { alert("O motor exige um arquivo anexo!"); document.getElementById('loader').classList.add('hidden'); return; }
                    form.append('file', fi.files[0]);
                } else {
                    let dataset = [];
                    document.querySelectorAll('#lab-grid tr').forEach(tr => {
                        const cellVals = Array.from(tr.querySelectorAll('input')).map(i => i.value.trim());
                        if(cellVals[0] && cellVals[1] && cellVals[2]) {
                            if(!cellVals[3]) cellVals[3] = 'nan'; dataset.push(cellVals.join(','));
                        }
                    });
                    if(dataset.length < 5) { alert("Base de dados manual insuficiente para regressão."); document.getElementById('loader').classList.add('hidden'); return; }
                    form.append('manual_dataset', dataset.join('\\n'));
                }

                try {
                    const resp = await fetch('/v3/scientific/engine', {method:'POST', body:form});
                    const d = await resp.json();
                    if(d.detail) throw new Error(d.detail);

                    excelOutput = d.xlsx_b64;
                    document.getElementById('res-sec').classList.remove('hidden');
                    document.getElementById('v-tb').innerText = d.out.temp + "°";
                    document.getElementById('v-r2').innerText = d.out.r2.toFixed(4);
                    document.getElementById('v-qme').innerText = d.out.qme.toFixed(9);
                    document.getElementById('h-lab').innerText = "🔬 Study Results: " + d.label;

                    Plotly.newPlot('gr1', [{x:d.chart.qx, y:d.chart.qy, mode:'lines+markers', line:{color:'black'}}], {title:'Mínimo Residual (Analítico)', font:{size:10}});
                    Plotly.newPlot('gr2', [{x:d.chart.rx, y:d.chart.ry, mode:'markers', marker:{color:'gray'}, name:'Data'},{x:d.chart.rx, y:d.chart.rp, mode:'lines', line:{color:'black', dash:'dot'}}], {title:'Ajuste Experimental (Linear)', font:{size:10}, showlegend:false});

                    // Gerar Tabela de Visualização de dados processados
                    let tableHTML = '<table class="w-full text-left text-[10px] font-mono"><thead class="bg-slate-50 border-b"><tr><th class="p-2 border-r">Data</th><th class="p-2 border-r text-center">T.Mín</th><th class="p-2 border-r text-center">T.Máx</th><th class="p-2 text-center">Variável (NF)</th></tr></thead><tbody>';
                    d.preview_rows.forEach(r => {
                        tableHTML += `<tr class="border-b"><td class="p-2 border-r font-black text-slate-500">${r.Data}</td><td class="p-2 border-r text-center font-bold">${r.Tmin}</td><td class="p-2 border-r text-center font-bold">${r.Tmax}</td><td class="p-2 text-center text-green-700 font-bold italic">${r.NF}</td></tr>`;
                    });
                    document.getElementById('v-preview').innerHTML = tableHTML + '</tbody></table>';

                    window.scrollTo({top: 0, behavior:'smooth'});
                } catch(e) {
                    alert("ALERTA CIENTÍFICO: Falha interna detectada.\\n" + e.message);
                } finally { document.getElementById('loader').classList.add('hidden'); }
            }

            function baixarResultados() {
                if(!excelOutput) return;
                const bstr = atob(excelOutput), bArr = new ArrayBuffer(bstr.length), u8 = new Uint8Array(bArr);
                for(let i=0; i<bstr.length; i++) u8[i] = bstr.charCodeAt(i);
                const b = new Blob([bArr], {type:'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'});
                const link = document.createElement('a'); link.href = window.URL.createObjectURL(b);
                link.download = `EstimaTB_Investigacao_${new Date().getTime()}.xlsx`; link.click();
            }
        </script>
        <style>.sheet-cell { width: 100%; border: 1px solid #f1f5f9; padding: 6px; text-align: center; outline: none; font-size: 11px; font-family: monospace; }</style>
    </body>
    </html>
    """.replace("URL_VAL", SURL).replace("KEY_VAL", SKEY)

# =========================================================================
# ⚙️ BLOCO 4: BACKEND ENGINE V3 (REFORÇADO)
# =========================================================================
@app.post("/v3/scientific/engine")
async def run_final_engine(
    file: UploadFile = None, manual_dataset: str = Form(None), analise_nome: str = Form(""),
    min: float = Form(0.0), max: float = Form(20.0), step: float = Form(0.5)
):
    try:
        if file:
            content = await file.read()
            df = pd.read_csv(BytesIO(content), sep=None, engine='python', decimal=',') if file.filename.endswith('.csv') else pd.read_excel(BytesIO(content))
        else:
            df = pd.read_csv(StringIO(manual_dataset), names=['Data','Tmin','Tmax','NF'], header=None)

        # Higiene Total (Normalização para o Motor)
        df.rename(columns=lambda x: 'Data' if fix_txt(x) == 'data' else x, inplace=True)
        df.rename(columns=lambda x: 'Tmin' if fix_txt(x) in ['tmin','tmín'] else x, inplace=True)
        df.rename(columns=lambda x: 'Tmax' if fix_txt(x) in ['tmax','tmáx'] else x, inplace=True)
        df.rename(columns=lambda x: 'NF' if fix_txt(x) in ['nf','variavel','variável'] else x, inplace=True)

        for col in ['Tmin','Tmax','NF']:
            df[col] = pd.to_numeric(df[col].astype(str).str.replace(',','.').replace('nan',np.nan), errors='coerce')
        
        df['Data'] = pd.to_datetime(df['Data'], dayfirst=True, errors='coerce')
        df = df.dropna(subset=['Data','Tmin','Tmax']).sort_values('Data').reset_index(drop=True)

        # ALERTA CIENTÍFICO 1: Consistência Térmica
        inverted = df[df['Tmin'] > df['Tmax']]
        if not inverted.empty:
            raise ValueError(f"Inconsistência climática detectada: Existem {len(inverted)} linhas onde T.Mín é maior que T.Máx. Revise seus dados de entrada.")

        # Amostragem da Fenologia
        valid_pheno = df.dropna(subset=['NF'])
        if len(valid_pheno) < 3:
            raise ValueError("O estudo precisa de ao menos 3 dias com anotações numéricas na coluna de Variável (NF). Verificamos apenas dados nulos ou vazios no arquivo anexado.")

        df['Tmed'] = (df['Tmin'] + df['Tmax']) / 2
        p_idx = valid_pheno.index
        results = []
        winner = None
        min_error_val = float('inf')

        t_range_scan = np.arange(min, max + step, step)
        for tb_it in t_range_scan:
            tb_it = round(float(tb_it), 2)
            sta_cum = (df['Tmed'] - tb_it).clip(lower=0).cumsum()
            
            # Dados sincronizados (pelo index real)
            X = sta_cum.loc[p_idx].values.reshape(-1, 1)
            y = df.loc[p_idx, 'NF'].values
            
            lr = LinearRegression().fit(X, y)
            preds = lr.predict(X)
            q_error = mean_squared_error(y, preds)
            
            results.append({'Tb': tb_it, 'R2': lr.score(X,y), 'QME': q_error})
            
            if q_error < min_error_val:
                min_error_val = q_error
                winner = {
                    'tb': tb_it, 'r2': lr.score(X,y), 'qme': q_error, 'a': lr.coef_[0], 'b': lr.intercept_,
                    'plot_x': sta_cum.loc[p_idx].tolist(), 'all_sta': sta_cum.tolist()
                }

        results_df = pd.DataFrame(results)
        
        # Datasets p/ Exportação
        xls_clima = df[['Data','Tmin','Tmax','Tmed']].copy()
        xls_clima['Soma_Termica_Otima'] = winner['all_sta']
        
        xls_pheno = pd.DataFrame({
            'Data': df.loc[p_idx, 'Data'],
            'Variavel_Observada': df.loc[p_idx, 'NF'],
            'STa_Sugerida': winner['plot_x']
        })

        # Correção do Bug de nomenclatura enviado na mensagem anterior
        xls_b64 = export_xlsx(xls_clima, results_df, xls_pheno, winner['tb'])

        return {
            "label": analise_nome or "Investigação Sem Título",
            "out": {"temp": winner['tb'], "r2": winner['r2'], "qme": winner['qme']},
            "chart": {
                "qx": results_df['Tb'].tolist(), "qy": results_df['QME'].tolist(),
                "rx": winner['plot_x'], "ry": valid_pheno['NF'].astype(float).tolist(),
                "rp": [float(val * winner['a'] + winner['b']) for val in winner['plot_x']]
            },
            "preview_rows": df.head(15).astype(str).to_dict(orient="records"),
            "xlsx_b64": xls_b64
        }
    except Exception as e:
        import traceback
        print(traceback.format_exc())
        return {"detail": str(e)}
