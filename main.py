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
# BLOCO BLINDADO - LOGIN E SEGURANÇA (Mantenha essas chaves)
# =========================================================================
S_URL = "https://iuhtopexunirguxmjiey.supabase.co"
S_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Iml1aHRvcGV4dW5pcmd1eG1qaWV5Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzE1MjIzNTcsImV4cCI6MjA4NzA5ODM1N30.EjDui9gQ5AlRaNpoVQisGUoXmK3j74gwzq9QSguxq78"
stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "")
EMAIL_ADMIN = "abielgm@icloud.com"

@app.get("/", response_class=HTMLResponse)
async def interface():
    # Usando .replace() para não ter conflito de chaves do Python/JS
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
            .excel-in { width: 100%; border: 1px solid #e5e7eb; padding: 6px; font-size: 11px; text-align: center; font-family: 'Courier New', monospace; outline: none; }
            .excel-in:focus { background: #f0fdf4; border: 1px solid #16a34a; }
            .header-cell { background: #f1f5f9; padding: 8px; font-size: 10px; font-weight: 800; border: 1px solid #e2e8f0; text-transform: uppercase; color: #475569; }
        </style>
    </head>
    <body class="bg-[#f8fafc] text-slate-800 font-sans min-h-screen">
        <div id="loader" class="hidden fixed inset-0 bg-white/90 z-50 flex flex-col items-center justify-center">
            <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-green-700 mb-4"></div>
            <p class="font-black text-green-800 animate-pulse italic uppercase tracking-tighter text-sm">Motor Científico em Processamento...</p>
        </div>

        <div class="max-w-6xl mx-auto p-4 md:p-10">
            <!-- LOGIN SECTION -->
            <div id="login-section" class="max-w-md mx-auto bg-white p-10 rounded-[2.5rem] shadow-2xl mt-12 border border-slate-200 text-center">
                <h1 class="text-4xl font-black text-green-700 italic mb-1 italic">EstimaTB🌿</h1>
                <p class="text-[9px] font-bold text-slate-300 uppercase tracking-widest mb-8 italic">Research Lab System</p>
                <div class="space-y-4">
                    <input type="email" id="email" placeholder="E-mail" class="w-full border-2 p-4 rounded-2xl outline-none focus:border-green-600 bg-slate-50">
                    <input type="password" id="password" placeholder="Senha" class="w-full border-2 p-4 rounded-2xl outline-none focus:border-green-600 bg-slate-50">
                    <button onclick="auth('login')" class="w-full bg-green-600 text-white py-4 rounded-2xl font-black shadow-lg hover:bg-green-700 transform active:scale-95 transition">ENTRAR</button>
                    <button onclick="toggleMode()" id="btnMode" class="text-green-600 font-bold text-[10px] uppercase tracking-widest mt-4">Cadastro</button>
                </div>
            </div>

            <!-- DASHBOARD -->
            <div id="main-section" class="hidden">
                <div class="bg-white p-6 rounded-[2rem] shadow-sm border border-slate-200 mb-6 flex justify-between items-center px-10">
                    <div><span class="text-[10px] text-slate-400 font-bold uppercase block italic">Authenticated</span><p id="user-display" class="font-black text-green-700 text-sm"></p></div>
                    <div id="adm-tag" class="hidden bg-green-50 text-green-700 border border-green-200 px-4 py-1 rounded-full text-[10px] font-black uppercase italic">✓ Administrador Master</div>
                    <button onclick="logout()" class="bg-red-50 text-red-500 font-black text-[10px] px-6 py-2 rounded-full border border-red-100 hover:bg-red-500 hover:text-white transition-all uppercase italic">Encerrar Lab</button>
                </div>

                <div class="grid lg:grid-cols-12 gap-8">
                    <!-- Config Side -->
                    <div class="lg:col-span-5 space-y-6">
                        <div class="bg-white p-8 rounded-[3rem] shadow-xl border">
                            <h3 class="font-black text-slate-800 text-xs uppercase mb-6 flex items-center italic underline decoration-green-300"><i class="fas fa-microscope mr-2 text-green-600"></i>Parâmetros Analíticos</h3>
                            
                            <input type="text" id="nome_analise" placeholder="Identificação (Ex: Anita 12 Época)" class="w-full border-2 p-4 rounded-2xl mb-6 text-sm font-bold focus:border-green-600 outline-none">

                            <div class="flex bg-slate-100 p-1 rounded-2xl mb-6 shadow-inner">
                                <button onclick="setTab('f')" id="tab-f" class="flex-1 py-3 text-[10px] font-black rounded-xl bg-white shadow-sm text-green-700 uppercase">Arquivo</button>
                                <button onclick="setTab('m')" id="tab-m" class="flex-1 py-3 text-[10px] font-black rounded-xl text-slate-400 uppercase tracking-tighter italic">Digitação</button>
                            </div>

                            <div id="ui-f"><input type="file" id="arquivo" class="block w-full border-2 border-dashed p-10 rounded-2xl bg-slate-50 cursor-pointer text-xs font-bold text-slate-400"></div>

                            <div id="ui-m" class="hidden">
                                <div class="bg-white rounded-2xl border overflow-hidden shadow-inner mb-4 max-h-96 overflow-y-auto">
                                    <table class="w-full" id="manual-table">
                                        <thead class="sticky top-0 shadow-sm">
                                            <tr>
                                                <th class="header-cell">Data</th>
                                                <th class="header-cell">Tmin</th>
                                                <th class="header-cell">Tmax</th>
                                                <th class="header-cell text-green-700 italic font-black">Variável (NF)</th>
                                            </tr>
                                        </thead>
                                        <tbody id="manual-body"></tbody>
                                    </table>
                                </div>
                                <div class="flex justify-between items-center mb-6">
                                    <button onclick="addRow(5)" class="text-[9px] font-black text-green-600 bg-green-50 px-4 py-2 rounded-xl hover:bg-green-100 uppercase">+ Adicionar Linhas</button>
                                    <button onclick="initManual()" class="text-[9px] font-black text-red-500 hover:underline uppercase italic">Limpar Planilha</button>
                                </div>
                            </div>

                            <div class="bg-slate-50 p-6 rounded-3xl border text-center shadow-inner mb-8">
                                <p class="text-[9px] font-black text-slate-400 uppercase mb-4 italic tracking-widest underline">Ajuste dos Parâmetros do Motor</p>
                                <div class="grid grid-cols-3 gap-2">
                                    <div class="flex flex-col"><label class="text-[8px] font-bold">Mín (°C)</label><input type="number" id="tmin" value="0.0" class="w-full border p-2 rounded-xl text-center font-bold"></div>
                                    <div class="flex flex-col"><label class="text-[8px] font-bold">Máx (°C)</label><input type="number" id="tmax" value="20.0" class="w-full border p-2 rounded-xl text-center font-bold"></div>
                                    <div class="flex flex-col"><label class="text-[8px] font-bold text-green-700 italic font-black">Passo</label><input type="number" id="passo" value="0.5" step="0.1" class="w-full border p-2 rounded-xl text-center font-bold text-green-600 border-green-200"></div>
                                </div>
                            </div>

                            <button onclick="executarAnalisar()" id="btnCalc" class="w-full bg-green-600 text-white py-5 rounded-[1.8rem] font-black text-xl shadow-xl hover:scale-105 transition-all uppercase tracking-tighter">ANALLISAR MODELO</button>
                        </div>
                    </div>

                    <!-- Resultado Side -->
                    <div id="results-view" class="lg:col-span-7 hidden">
                        <div class="bg-white p-10 rounded-[3rem] shadow-2xl border-t-[14px] border-slate-900 h-fit sticky top-10">
                            <h2 class="text-xl font-black italic border-b pb-4 mb-10 text-slate-800" id="nome-final">Modelagem Agrometeorológica</h2>
                             <div class="grid grid-cols-3 gap-4 mb-10">
                                <div class="bg-slate-50 p-6 rounded-3xl border-2 border-slate-50 text-center shadow-inner">
                                    <span class="text-[10px] font-black text-slate-400 italic block mb-2 uppercase">Temperatura Basal</span>
                                    <p id="v-tb" class="text-4xl font-black font-mono tracking-tighter">--</p>
                                </div>
                                <div class="bg-slate-50 p-6 rounded-3xl border-2 border-slate-100 text-center shadow-inner">
                                    <span class="text-[10px] font-black text-green-700 block mb-2 uppercase tracking-tighter">Coeficiente R²</span>
                                    <p id="v-r2" class="text-4xl font-black font-mono text-green-700 tracking-tighter">--</p>
                                </div>
                                <div class="bg-slate-50 p-6 rounded-3xl border-2 border-slate-50 text-center shadow-inner">
                                    <span class="text-[10px] font-black text-slate-400 block mb-2 italic">Mínimo QME</span>
                                    <p id="v-qme" class="text-[12px] font-bold font-mono">--</p>
                                </div>
                             </div>
                             
                             <div class="grid md:grid-cols-1 gap-10">
                                <div id="gr-qme" class="h-64 bg-slate-50 rounded-2xl border-2"></div>
                                <div id="gr-reg" class="h-64 bg-slate-50 rounded-2xl border-2"></div>
                             </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <script>
            const SUP_URL = "SET_URL"; const SUP_KEY = "SET_KEY"; const ADM_MAIL = "abielgm@icloud.com";
            const _supa = supabase.createClient(SUP_URL, SUP_KEY);
            let tab = 'f'; let aMode = 'login';

            function initManual() { 
                document.getElementById('manual-body').innerHTML = ''; addRow(20); 
            }
            function addRow(n) {
                const b = document.getElementById('manual-body');
                for(let i=0;i<n;i++) {
                    const r = document.createElement('tr');
                    r.innerHTML = '<td><input type="text" class="excel-in d-in"></td><td><input type="text" class="excel-in tmi-in"></td><td><input type="text" class="excel-in tma-in"></td><td><input type="text" class="excel-in var-in"></td>';
                    b.appendChild(r);
                }
            }
            initManual();

            // FUNÇÃO COLAR EXCEL GLOBAL
            document.addEventListener('paste', function(e) {
                if(e.target.classList.contains('excel-in')) {
                    e.preventDefault();
                    const text = e.clipboardData.getData('text');
                    const rows = text.split(/\\r?\\n/);
                    let currTr = e.target.closest('tr');
                    rows.forEach(r => {
                        if(r.trim()==='') return;
                        const cols = r.split('\\t');
                        const ins = currTr.querySelectorAll('input');
                        cols.forEach((v, idx) => { if(ins[idx]) ins[idx].value = v.trim(); });
                        currTr = currTr.nextElementSibling;
                        if(!currTr) { addRow(1); currTr = document.getElementById('manual-body').lastElementChild; }
                    });
                }
            });

            async function auth(t) {
                const email = document.getElementById('email').value, password = document.getElementById('password').value;
                document.getElementById('loader').classList.remove('hidden');
                let r = (t === 'login') ? await _supa.auth.signInWithPassword({email, password}) : await _supa.auth.signUp({email, password});
                if(r.error) { alert("Autenticação: " + r.error.message); document.getElementById('loader').classList.add('hidden'); }
                else location.reload();
            }

            async function checkU() {
                const {data:{user}} = await _supa.auth.getUser();
                if(user) {
                    document.getElementById('login-section').classList.add('hidden');
                    document.getElementById('main-section').classList.remove('hidden');
                    document.getElementById('user-display').innerText = user.email.toLowerCase();
                    if(user.email.toLowerCase() === ADM_MAIL.toLowerCase()) document.getElementById('adm-tag').classList.remove('hidden');
                }
            }
            checkU();
            async function logout() { 
                await _supa.auth.signOut(); 
                localStorage.clear();
                window.location.replace('/'); 
            }

            function setTab(m) {
                tab = m;
                document.getElementById('tab-f').classList.toggle('bg-white', m=='f');
                document.getElementById('tab-m').classList.toggle('bg-white', m=='m');
                document.getElementById('ui-f').classList.toggle('hidden', m=='m');
                document.getElementById('ui-m').classList.toggle('hidden', m=='f');
            }

            async function executarAnalisar() {
                document.getElementById('loader').classList.remove('hidden');
                const fd = new FormData();
                fd.append('analise', document.getElementById('analise_nome').value);
                fd.append('tmin', document.getElementById('tmin').value);
                fd.append('tmax', document.getElementById('tmax').value);
                fd.append('passo', document.getElementById('passo').value);

                if(tab === 'f') {
                    const f = document.getElementById('arquivo').files[0];
                    if(!f) { alert("Anexe seu arquivo científico!"); document.getElementById('loader').classList.add('hidden'); return; }
                    fd.append('file', f);
                } else {
                    let dArr = [];
                    document.querySelectorAll('#manual-body tr').forEach(tr => {
                        const vals = Array.from(tr.querySelectorAll('input')).map(i => i.value.trim());
                        if(vals[0] && vals[1]) dArr.push(vals.join(','));
                    });
                    if(dArr.length < 5) { alert("Dados insuficientes!"); document.getElementById('loader').classList.add('hidden'); return; }
                    fd.append('manual_data', dArr.join('\\n'));
                }

                try {
                    const resp = await fetch('/analisar', {method:'POST', body:fd});
                    const d = await resp.json();
                    if(d.detail) throw new Error(d.detail);

                    document.getElementById('results-view').classList.remove('hidden');
                    document.getElementById('v-tb').innerText = d.best.t + "°C";
                    document.getElementById('v-r2').innerText = d.best.r2.toFixed(4);
                    document.getElementById('v-qme').innerText = d.best.qme.toFixed(6);
                    document.getElementById('nome-final').innerText = "🔬 Lab Analysis: " + d.nome;

                    // Plotly P&B Científico
                    Plotly.newPlot('gr-qme', [{x: d.q.t, y: d.q.q, mode: 'lines+markers', line:{color:'black'}, marker:{color:'black'}}], {
                        title: '<b>QME vs Temperatura de Referência</b>', font:{size:10}, margin:{t:40, b:40}, xaxis:{title:'Tb (°C)'}
                    });

                    Plotly.newPlot('gr-reg', [
                        {x: d.reg.x, y: d.reg.y, mode: 'markers', marker:{color:'gray', symbol:'circle-open'}, name:'Obs.'},
                        {x: d.reg.x, y: d.reg.p, mode: 'lines', line:{color:'black', dash:'dot'}, name:'Linha'}
                    ], {
                        title: '<b>Relação Experimental: NF vs STa</b>', font:{size:10}, margin:{t:40, b:40}, showlegend:false, xaxis:{title:'Graus-Dia Acumulados (STa)'}, yaxis:{title:'Número de Folhas (NF)'}
                    });

                    window.scrollTo({ top: document.body.scrollHeight, behavior: 'smooth' });

                } catch(e) {
                    alert("ALERTA CIENTÍFICO: Falha técnica na regressão.\\nMOTIVOS POSSÍVEIS:\\n1. Menos de 3 medições informadas em NF.\\n2. Vírgulas ou espaços inválidos no campo Tmin/Tmax.\\n3. Variável (NF) não está aumentando conforme a planta cresce.");
                } finally { document.getElementById('loader').classList.add('hidden'); }
            }
        </script>
    </body>
    </html>
    """.replace("SET_URL", S_URL).replace("SET_KEY", S_KEY)
    return html_template

# =========================================================================
# BACKEND: MOTOR DE CÁLCULO TRATADO PARA "EMPTY CELLS"
# =========================================================================
@app.post("/analisar")
async def analisar(
    file: UploadFile = None, manual_data: str = Form(None),
    analise: str = Form(""), tmin: float = Form(0.0), tmax: float = Form(20.0), passo: float = Form(0.5)
):
    try:
        if file:
            content = await file.read()
            # Tenta CSV e depois Excel. O segredo é dayfirst=True
            if file.filename.endswith('.csv'):
                df = pd.read_csv(BytesIO(content), sep=None, engine='python', decimal=',')
            else:
                df = pd.read_excel(BytesIO(content))
        else:
            # Caso Manual
            df = pd.read_csv(StringIO(manual_data), names=['Data', 'Tmin', 'Tmax', 'NF'], header=None)
        
        # 1. Limpeza Fundamental
        df = rename_columns(df)
        df.columns = [str(c).strip() for c in df.columns]
        
        # 2. Tratamento Crítico de Números (Lidar com vírgulas PT-BR e espaços)
        for col in ['Tmin', 'Tmax', 'NF']:
            df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', '.').replace('nan', np.nan), errors='coerce')
        
        # 3. Tratamento Crítico de Datas (Ajustado para DD/MM/YYYY)
        df['Data'] = pd.to_datetime(df['Data'], dayfirst=True, errors='coerce')
        
        # 4. Remover lixo sem temperatura (isso mantém o NF=NaN, que é o que você quer!)
        df = df.dropna(subset=['Data', 'Tmin', 'Tmax'])

        # Chamar motor.py
        res = executar_calculo_tb(df, tmin, tmax, passo)
        
        # Preparar Gráficos
        mdf = pd.DataFrame(res['tabela_meteorologica'])
        best_t_found = float(res['melhor_resultado']['Temperatura (ºC)'])
        calc_cols = [float(c) for c in mdf.columns if c not in ['Dia', 'Mês', 'Ano', 'Tmin', 'Tmax', 'Tmed']]
        # Acha a coluna mais próxima matematicamente do Tb encontrado
        idx_target = np.abs(np.array(calc_cols) - best_t_found).argmin()
        col_str = str(calc_cols[idx_target])
        
        # Pegar apenas as linhas onde realmente houve avaliação de campo (NF existe)
        indices_observados = [i for i, v in enumerate(df['NF']) if not pd.isna(v)]

        return {
            "nome": analise or "Sem Identificação",
            "best": {"t": res['melhor_resultado']['Temperatura (ºC)'], "r2": res['melhor_resultado']['R2'], "qme": res['melhor_resultado']['QME']},
            "q": {"t": [x['Temperatura (ºC)'] for x in res['tabela_erros']], "q": [x['QME'] for x in res['tabela_erros']]},
            "reg": {
                "x": [float(mdf.iloc[i][col_str]) for i in indices_observados],
                "y": [float(x) for x in df['NF'].dropna().tolist()],
                "p": [float(mdf.iloc[i][col_str] * res['melhor_resultado']['Coef_Angular'] + res['melhor_resultado']['Intercepto']) for i in indices_observados]
            }
        }
    except Exception as e:
        print(f"CRÍTICO: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
