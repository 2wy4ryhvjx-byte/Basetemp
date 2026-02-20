import os
import stripe
import pandas as pd
import numpy as np
from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from fastapi.responses import HTMLResponse
from io import BytesIO, StringIO
from motor import executar_calculo_tb, rename_columns

app = FastAPI()

# =========================================================================
# BLOCO DE SEGURANÇA E LOGIN (PROTEGIDO)
# =========================================================================
S_URL = "https://iuhtopexunirguxmjiey.supabase.co"
S_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Iml1aHRvcGV4dW5pcmd1eG1qaWV5Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzE1MjIzNTcsImV4cCI6MjA4NzA5ODM1N30.EjDui9gQ5AlRaNpoVQisGUoXmK3j74gwzq9QSguxq78"
stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "")
EMAIL_ADMIN = "abielgm@icloud.com"

@app.get("/", response_class=HTMLResponse)
async def interface():
    html_content = """
    <!DOCTYPE html>
    <html lang="pt-br">
    <head>
        <meta charset="UTF-8"><title>EstimaTB Pro 🌿</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <script src="https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2"></script>
        <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
        <style>
            .spreadsheet-input { width: 100%; border: 1px solid #e2e8f0; padding: 6px; font-size: 11px; font-family: monospace; outline: none; }
            .spreadsheet-input:focus { background-color: #f0fdf4; border-color: #16a34a; }
            .col-header { background: #f8fafc; font-size: 10px; font-weight: 900; text-transform: uppercase; color: #64748b; padding: 8px; text-align: center; border: 1px solid #e2e8f0; }
        </style>
    </head>
    <body class="bg-[#F3F4F6] font-sans min-h-screen">
        
        <div id="loading" class="hidden fixed inset-0 bg-white/95 flex items-center justify-center z-50 flex-col">
            <div class="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-green-700 mb-4"></div>
            <p class="font-black text-green-900 animate-pulse italic">PROCESSANDO MODELO CIENTÍFICO...</p>
        </div>

        <div class="max-w-6xl mx-auto p-4 md:p-10">
            <!-- LOGIN SECTION (PROTECTED) -->
            <div id="login-section" class="max-w-md mx-auto bg-white p-10 rounded-[2.5rem] shadow-2xl mt-12 text-center border">
                <h1 class="text-4xl font-black text-green-700 italic mb-2 tracking-tighter uppercase underline decoration-yellow-400">EstimaTB🌿</h1>
                <p class="text-[9px] font-bold text-slate-300 uppercase tracking-widest mb-8">System Secured Laboratory</p>
                <div class="space-y-4">
                    <input type="email" id="email" placeholder="E-mail" class="w-full border-2 p-4 rounded-2xl outline-none focus:border-green-600 bg-slate-50">
                    <input type="password" id="password" placeholder="Senha" class="w-full border-2 p-4 rounded-2xl outline-none focus:border-green-600 bg-slate-50">
                    <button onclick="handleAuth('login')" id="btnLogin" class="w-full bg-green-600 text-white py-4 rounded-2xl font-black shadow-lg">ENTRAR</button>
                    <button onclick="toggleMode()" id="btnSwitch" class="text-green-600 font-bold text-[10px] uppercase mt-2">Cadastro</button>
                </div>
            </div>

            <!-- DASHBOARD -->
            <div id="main-section" class="hidden">
                <div class="flex justify-between items-center bg-white p-6 rounded-[2rem] shadow-sm border mb-8 px-10">
                    <p class="text-slate-500 font-bold text-xs italic italic">Pesquisador: <span id="user-display" class="text-green-700 font-black not-italic"></span></p>
                    <div id="admin-tag" class="hidden bg-green-50 text-green-700 text-[10px] font-black px-6 py-1 rounded-full border border-green-200 uppercase tracking-tighter">Administrador Master</div>
                    <button onclick="logout()" class="text-red-500 font-black text-[10px] uppercase underline transition-all">Sair</button>
                </div>

                <div class="grid grid-cols-1 lg:grid-cols-12 gap-8">
                    <!-- Config e Input -->
                    <div class="lg:col-span-5 space-y-6">
                        <div class="bg-white p-8 rounded-[2.5rem] shadow-xl border relative">
                            <h3 class="font-black text-slate-800 text-xs uppercase mb-6 flex items-center border-b pb-4 italic"><i class="fas fa-microscope mr-2 text-green-600"></i>Parâmetros da Amostra</h3>
                            
                            <input type="text" id="analise_nome" placeholder="Identificação da Época/Amostra" class="w-full border-2 p-4 rounded-2xl mb-6 bg-slate-50 text-sm focus:border-green-600 outline-none">

                            <div class="flex bg-slate-100 p-1 rounded-2xl mb-6 shadow-inner">
                                <button onclick="setMode('f')" id="btn-f" class="flex-1 py-3 text-[10px] font-black rounded-xl bg-white shadow-md text-green-700 uppercase transition-all">Anexo de Arquivo</button>
                                <button onclick="setMode('m')" id="btn-m" class="flex-1 py-3 text-[10px] font-black rounded-xl text-slate-400 uppercase transition-all tracking-tighter">Planilha Manual</button>
                            </div>

                            <div id="ui-f"><input type="file" id="arquivo" class="block w-full border-2 border-dashed p-10 rounded-2xl bg-slate-50 cursor-pointer"></div>

                            <div id="ui-m" class="hidden">
                                <p class="text-[9px] font-black text-slate-400 uppercase mb-3 italic">Cole seus dados do Excel abaixo (Ctrl+V)</p>
                                <div class="overflow-x-auto rounded-xl border mb-4 shadow-sm" id="grid-parent">
                                    <table class="w-full border-collapse" id="spreadsheet">
                                        <thead>
                                            <tr>
                                                <th class="col-header">Data</th>
                                                <th class="col-header">Tmin</th>
                                                <th class="col-header">Tmax</th>
                                                <th class="col-header">Variável (NF)</th>
                                            </tr>
                                        </thead>
                                        <tbody id="grid-body">
                                            <!-- Injetado por JS -->
                                        </tbody>
                                    </table>
                                </div>
                                <button onclick="resetTable()" class="text-[8px] font-black uppercase text-red-500 hover:underline">Limpar Tabela</button>
                            </div>

                            <div class="bg-slate-50 p-6 rounded-3xl mt-8 border shadow-inner">
                                <p class="text-[9px] font-black text-slate-400 uppercase italic mb-4 text-center">Filtros de Passo e Temperatura</p>
                                <div class="grid grid-cols-3 gap-3">
                                    <div class="flex flex-col"><label class="text-[8px] font-black text-gray-500 uppercase ml-1">Tb Min</label><input type="number" id="tmin" value="0.0" class="w-full border p-2 rounded-xl text-center font-bold"></div>
                                    <div class="flex flex-col"><label class="text-[8px] font-black text-gray-500 uppercase ml-1">Tb Max</label><input type="number" id="tmax" value="20.0" class="w-full border p-2 rounded-xl text-center font-bold"></div>
                                    <div class="flex flex-col"><label class="text-[8px] font-black text-gray-500 uppercase ml-1 underline text-green-700">Passo</label><input type="number" id="passo" value="0.5" step="0.1" class="w-full border p-2 rounded-xl text-center font-bold border-green-100"></div>
                                </div>
                            </div>

                            <button id="btnCalc" onclick="executarCalculo()" class="mt-8 w-full bg-green-600 text-white py-5 rounded-2xl font-black text-xl shadow-xl hover:scale-105 transition-all uppercase">Analisar Dados</button>
                        </div>
                    </div>

                    <!-- Gráficos e Saída -->
                    <div id="results-col" class="lg:col-span-7 hidden animate-in slide-in-from-right">
                        <div class="bg-white p-8 rounded-[3rem] shadow-2xl border-t-[12px] border-slate-900 mb-8">
                            <h2 class="text-xl font-black italic border-b pb-4 mb-8" id="nome-exibicao">🔬 Laboratório Virtual</h2>
                             <div class="grid grid-cols-3 gap-4 mb-8">
                                <div class="bg-slate-50 p-6 rounded-2xl text-center shadow-inner border"><span class="text-[9px] font-black text-slate-400 block mb-1 uppercase tracking-tighter italic">Temp. Basal (Tb)</span><p id="v-tb" class="text-4xl font-black font-mono">--</p></div>
                                <div class="bg-slate-50 p-6 rounded-2xl text-center shadow-inner border"><span class="text-[9px] font-black text-slate-400 block mb-1 uppercase tracking-tighter italic">Ajuste (R²)</span><p id="v-r2" class="text-4xl font-black font-mono text-green-700">--</p></div>
                                <div class="bg-slate-50 p-6 rounded-2xl text-center shadow-inner border"><span class="text-[9px] font-black text-slate-400 block mb-1 uppercase tracking-tighter italic">Min QME</span><p id="v-qme" class="text-xs font-bold font-mono">--</p></div>
                             </div>
                             
                             <div class="grid grid-cols-1 md:grid-cols-2 gap-4 h-[350px]">
                                <div id="plt-qme" class="bg-white rounded-2xl shadow-inner border h-full w-full overflow-hidden"></div>
                                <div id="plt-reg" class="bg-white rounded-2xl shadow-inner border h-full w-full overflow-hidden"></div>
                             </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <script>
            const _supa = supabase.createClient("VARIABLE_SURL", "VARIABLE_SKEY");
            const MASTER = "abielgm@icloud.com";
            let modeInput = 'f';

            function initGrid() {
                const tbody = document.getElementById('grid-body');
                tbody.innerHTML = '';
                for(let i=0; i<8; i++) { addGridRow(); }
            }
            function addGridRow() {
                const tr = document.createElement('tr');
                tr.innerHTML = `<td><input type="text" class="spreadsheet-input dat-c"></td><td><input type="text" class="spreadsheet-input tmi-c"></td><td><input type="text" class="spreadsheet-input tma-c"></td><td><input type="text" class="spreadsheet-input var-c"></td>`;
                document.getElementById('grid-body').appendChild(tr);
            }
            function resetTable() { initGrid(); }
            initGrid();

            // SUPORTE AO CTRL+V DO EXCEL
            document.addEventListener('paste', function(e) {
                if(e.target.classList.contains('spreadsheet-input')) {
                    e.preventDefault();
                    const clipboard = e.clipboardData.getData('text');
                    const rows = clipboard.split('\\n');
                    let startTr = e.target.closest('tr');
                    
                    rows.forEach(rowText => {
                        if(rowText.trim() === '') return;
                        const cells = rowText.split('\\t');
                        const inputs = startTr.querySelectorAll('input');
                        cells.forEach((val, idx) => { if(inputs[idx]) inputs[idx].value = val.trim(); });
                        
                        startTr = startTr.nextElementSibling;
                        if(!startTr && rows.length > 0) { addGridRow(); startTr = document.getElementById('grid-body').lastElementChild; }
                    });
                }
            });

            function setMode(m) {
                modeInput = m;
                document.getElementById('btn-f').classList.toggle('bg-white', m=='f'); document.getElementById('btn-f').classList.toggle('text-green-700', m=='f');
                document.getElementById('btn-m').classList.toggle('bg-white', m=='m'); document.getElementById('btn-m').classList.toggle('text-green-700', m=='m');
                document.getElementById('ui-f').classList.toggle('hidden', m=='m');
                document.getElementById('ui-m').classList.toggle('hidden', m=='f');
            }

            async function handleAuth(t) {
                const e = document.getElementById('email').value, p = document.getElementById('password').value;
                document.getElementById('loading').classList.remove('hidden');
                let r = (t === 'login') ? await _supa.auth.signInWithPassword({email:e, password:p}) : await _supa.auth.signUp({email:e, password:p});
                if(r.error) { alert("Autenticação Falhou: " + r.error.message); document.getElementById('loading').classList.add('hidden'); }
                else location.reload();
            }

            async function checkS() {
                const {data:{user}} = await _supa.auth.getUser();
                if(user) {
                    document.getElementById('login-section').classList.add('hidden');
                    document.getElementById('main-section').classList.remove('hidden');
                    document.getElementById('user-display').innerText = user.email.toLowerCase();
                    if(user.email.toLowerCase() === MASTER.toLowerCase()) document.getElementById('admin-tag').classList.remove('hidden');
                }
            }
            checkS();
            async function logout() { await _supa.auth.signOut(); window.location.replace('/'); }

            async function executarCalculo() {
                document.getElementById('loading').classList.remove('hidden');
                const fd = new FormData();
                fd.append('analise', document.getElementById('analise_nome').value);
                fd.append('tmin', document.getElementById('tmin').value);
                fd.append('tmax', document.getElementById('tmax').value);
                fd.append('passo', document.getElementById('passo').value);

                if(modeInput === 'f') {
                    const f = document.getElementById('arquivo').files[0];
                    if(!f) { alert("Anexe o arquivo meteorológico!"); document.getElementById('loading').classList.add('hidden'); return; }
                    fd.append('file', f);
                } else {
                    let rowsCSV = [];
                    document.querySelectorAll('#grid-body tr').forEach(tr => {
                        const vals = Array.from(tr.querySelectorAll('input')).map(i => i.value.trim());
                        if(vals[0] && vals[1]) rowsCSV.push(vals.join(','));
                    });
                    if(rowsCSV.length < 3) { alert("Planilha incompleta!"); document.getElementById('loading').classList.add('hidden'); return; }
                    fd.append('manual_data', rowsCSV.join('\\n'));
                }

                try {
                    const res = await fetch('/analisar', {method:'POST', body:fd});
                    const d = await res.json();
                    if(d.detail) throw new Error(d.detail);

                    document.getElementById('results-col').classList.remove('hidden');
                    document.getElementById('v-tb').innerText = d.best.t + "°C";
                    document.getElementById('v-r2').innerText = d.best.r2.toFixed(4);
                    document.getElementById('v-qme').innerText = d.best.qme.toFixed(8);
                    document.getElementById('nome-exibicao').innerText = "🔬 Result: " + (d.nome || "Análise Geral");

                    Plotly.newPlot('plt-qme', [{x:d.q.t, y:d.q.q, mode:'lines+markers', line:{color:'black'}}], {title:'Mínimo QME', margin:{t:40,b:40,l:40,r:20}});
                    Plotly.newPlot('plt-reg', [{x:d.reg.x, y:d.reg.y, mode:'markers', marker:{color:'gray'}},{x:d.reg.x, y:d.reg.p, mode:'lines', line:{color:'black', dash:'dot'}}], {title:'Ajuste Linear', showlegend:false, margin:{t:40,b:40,l:40,r:20}});

                } catch(e) {
                    alert("ALERTA CIENTÍFICO: Falha na análise. Verifique os valores de Variável (devem ser cumulativos ou possuir ao menos 3 observações).");
                } finally { document.getElementById('loading').classList.add('hidden'); }
            }
        </script>
    </body>
    </html>
    """.replace("VARIABLE_SURL", S_URL).replace("VARIABLE_SKEY", S_KEY)
    return html_content

@app.post("/analisar")
async def analisar(
    file: UploadFile = None, manual_data: str = Form(None),
    analise: str = Form(""), tmin: float = Form(0.0), tmax: float = Form(20.0), passo: float = Form(0.5)
):
    try:
        if file:
            content = await file.read()
            df = pd.read_csv(BytesIO(content), sep=None, engine='python') if file.filename.endswith('.csv') else pd.read_excel(BytesIO(content))
        else:
            df = pd.read_csv(StringIO(manual_data), names=['Data', 'Tmin', 'Tmax', 'NF'], header=None)

        df = rename_columns(df)
        df['Data'] = pd.to_datetime(df['Data'], errors='coerce')
        # Limpeza para evitar NaN que quebram o cálculo manual
        df = df.dropna(subset=['Data', 'Tmin', 'Tmax'])
        
        res = executar_calculo_tb(df, tmin, tmax, passo)
        mdf = pd.DataFrame(res['tabela_meteorologica'])
        # Ajuste inteligente para achar coluna decimal correta
        melhor_val = float(res['melhor_resultado']['Temperatura (ºC)'])
        numeric_cols = [float(c) for c in mdf.columns if c not in ['Dia', 'Mês', 'Ano', 'Tmin', 'Tmax', 'Tmed']]
        best_col_name = str(numeric_cols[np.abs(np.array(numeric_cols) - melhor_val).argmin()])
        
        idx = [i for i, v in enumerate(df['NF']) if not pd.isna(v) and v != ""]

        return {
            "nome": analise,
            "best": {"t": res['melhor_resultado']['Temperatura (ºC)'], "r2": res['melhor_resultado']['R2'], "qme": res['melhor_resultado']['QME']},
            "q": {"t": [x['Temperatura (ºC)'] for x in res['tabela_erros']], "q": [x['QME'] for x in res['tabela_erros']]},
            "reg": {
                "x": [float(mdf.iloc[i][best_col_name]) for i in idx],
                "y": [float(x) for x in df['NF'].iloc[idx].tolist()],
                "p": [float(mdf.iloc[i][best_col_name] * res['melhor_resultado']['Coef_Angular'] + res['melhor_resultado']['Intercepto']) for i in idx]
            }
        }
    except Exception as e:
        return {"detail": str(e)}
