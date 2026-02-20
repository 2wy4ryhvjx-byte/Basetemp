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
# BLOCO DE SEGURANÇA E LOGIN (BLINDADO - NÃO MODIFICAR)
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
            .grid-input { width: 100%; border: none; background: transparent; padding: 4px; text-align: center; font-size: 12px; }
            .grid-input:focus { outline: 2px solid #16a34a; background: #f0fdf4; }
            tr:hover { background-color: #f9fafb; }
        </style>
    </head>
    <body class="bg-[#F3F4F6] font-sans min-h-screen text-slate-800">
        
        <div id="loading" class="hidden fixed inset-0 bg-white/90 flex items-center justify-center z-50 flex-col">
            <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-green-700 mb-4"></div>
            <p class="font-black text-green-900 animate-pulse italic uppercase">Processando Amostra Científica...</p>
        </div>

        <div class="max-w-6xl mx-auto p-4 md:p-10">
            <!-- LOGIN SECTION -->
            <div id="login-section" class="max-w-md mx-auto bg-white p-10 rounded-[2.5rem] shadow-2xl mt-12 text-center border">
                <h1 class="text-4xl font-black text-green-700 italic mb-2 uppercase underline decoration-yellow-400">EstimaTB🌿</h1>
                <p class="text-[9px] font-bold text-slate-300 uppercase tracking-widest mb-8">Professional Environment</p>
                <div class="space-y-4">
                    <input type="email" id="email" placeholder="E-mail Acadêmico" class="w-full border-2 p-4 rounded-2xl outline-none focus:border-green-600 bg-slate-50 shadow-inner">
                    <input type="password" id="password" placeholder="Senha" class="w-full border-2 p-4 rounded-2xl outline-none focus:border-green-600 bg-slate-50 shadow-inner">
                    <button onclick="handleAuth('login')" id="btnLogin" class="w-full bg-green-600 text-white py-4 rounded-2xl font-black shadow-lg hover:bg-green-700 active:scale-95 transition-all">ENTRAR NO LAB</button>
                    <button onclick="toggleMode()" id="btnSwitch" class="text-green-600 font-bold text-[10px] uppercase mt-2 hover:underline">Solicitar Novo Acesso</button>
                </div>
            </div>

            <!-- DASHBOARD -->
            <div id="main-section" class="hidden">
                <div class="flex flex-col md:flex-row justify-between items-center bg-white p-6 rounded-[2rem] shadow-sm border mb-6 px-10">
                    <p class="text-slate-500 font-bold text-xs italic">Researcher: <span id="user-display" class="text-green-700 font-black not-italic"></span></p>
                    <div id="admin-tag" class="hidden bg-green-100 text-green-700 text-[10px] font-black px-4 py-1 rounded-full border border-green-200">ADMINISTRADOR MASTER RECONHECIDO</div>
                    <button onclick="logout()" class="text-red-500 font-black text-[10px] hover:scale-105 uppercase transition-all underline">Encerrar Sessão</button>
                </div>

                <div class="grid grid-cols-1 lg:grid-cols-12 gap-8">
                    <!-- Config Side -->
                    <div class="lg:col-span-5 space-y-6">
                        <div class="bg-white p-8 rounded-[2.5rem] shadow-xl border">
                            <h3 class="font-black text-slate-800 text-xs uppercase mb-6 flex items-center border-b pb-4"><i class="fas fa-database mr-2 text-green-600"></i>Configurações e Entrada de Dados</h3>
                            
                            <input type="text" id="analise_nome" placeholder="Identificação da Amostra (Opcional)" class="w-full border-2 p-4 rounded-2xl mb-6 bg-slate-50 text-sm focus:border-green-600 outline-none">

                            <select id="mode-data" onchange="toggleInputs()" class="w-full border-2 p-4 rounded-2xl mb-6 bg-white text-xs font-black uppercase tracking-widest cursor-pointer shadow-sm">
                                <option value="f">Importar Planilha (Excel ou CSV)</option>
                                <option value="m">Digitação Direta em Planilha</option>
                            </select>

                            <div id="div-f" class="mb-6">
                                <input type="file" id="arquivo" class="block w-full border-2 border-dashed p-6 rounded-2xl bg-slate-50">
                                <p class="text-[9px] text-slate-400 mt-2 italic px-2">Aceita colunas: Data, Tmin, Tmax, NF</p>
                            </div>

                            <!-- PLANILHA MANUAL -->
                            <div id="div-m" class="hidden mb-6">
                                <div class="border rounded-2xl overflow-hidden shadow-inner bg-gray-50 mb-2">
                                    <table class="w-full border-collapse" id="manual-table">
                                        <thead class="bg-gray-100 border-b">
                                            <tr>
                                                <th class="text-[9px] py-2 uppercase font-black text-gray-500 border-r">Data</th>
                                                <th class="text-[9px] py-2 uppercase font-black text-gray-500 border-r">Tmin</th>
                                                <th class="text-[9px] py-2 uppercase font-black text-gray-500 border-r">Tmax</th>
                                                <th class="text-[9px] py-2 uppercase font-black text-gray-500">Variável</th>
                                            </tr>
                                        </thead>
                                        <tbody id="table-body">
                                            <!-- Linhas serão injetadas via JS -->
                                        </tbody>
                                    </table>
                                </div>
                                <button onclick="addRow()" class="w-full text-[9px] font-black text-green-600 border border-green-200 bg-green-50 rounded-xl py-2 mb-4 hover:bg-green-100 uppercase">+ Adicionar Linha</button>
                            </div>

                            <div class="bg-slate-50 p-6 rounded-3xl border mb-8 text-center shadow-inner">
                                <p class="text-[9px] font-black text-slate-400 uppercase italic mb-4 underline">Ajustes Finos de Referência (Opcional)</p>
                                <div class="grid grid-cols-3 gap-3">
                                    <div><label class="text-[8px] font-bold block mb-1">Tb Mín</label><input type="number" id="tmin" value="0.0" class="w-full border p-2 rounded-lg font-bold text-center"></div>
                                    <div><label class="text-[8px] font-bold block mb-1">Tb Máx</label><input type="number" id="tmax" value="20.0" class="w-full border p-2 rounded-lg font-bold text-center"></div>
                                    <div><label class="text-[8px] font-bold block mb-1">Passo</label><input type="number" id="passo" value="0.5" step="0.1" class="w-full border p-2 rounded-lg font-bold text-center text-green-700"></div>
                                </div>
                            </div>

                            <button id="btnCalc" onclick="calcular()" class="w-full bg-green-600 text-white py-5 rounded-[1.5rem] font-black text-xl shadow-xl hover:scale-105 transition-all uppercase tracking-tighter">ANALLISAR MODELO</button>
                        </div>
                    </div>

                    <!-- Gráficos Principal -->
                    <div id="result-view" class="lg:col-span-7 hidden space-y-6">
                        <div class="bg-white p-8 rounded-[3rem] shadow-2xl border-t-[12px] border-slate-900 relative">
                             <h3 id="view-name-display" class="text-xl font-black italic tracking-tighter text-slate-800 border-b pb-4 mb-8">🔬 Análise Científica</h3>
                             <div class="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
                                <div class="bg-slate-50 p-6 rounded-3xl border text-center shadow-inner"><p class="text-[9px] font-black text-slate-400">Tb Encontrada</p><p id="r-tb" class="text-4xl font-black font-mono">--</p></div>
                                <div class="bg-slate-50 p-6 rounded-3xl border text-center shadow-inner"><p class="text-[9px] font-black text-slate-400">Ajuste R²</p><p id="r-r2" class="text-4xl font-black font-mono text-green-700">--</p></div>
                                <div class="bg-slate-50 p-6 rounded-3xl border text-center shadow-inner"><p class="text-[9px] font-black text-slate-400 italic font-bold">Mínimo QME</p><p id="r-qme" class="text-lg font-bold font-mono">--</p></div>
                             </div>
                             
                             <div class="grid grid-cols-1 md:grid-cols-2 gap-4 h-[420px]">
                                <div id="gr-qme" class="border border-slate-50 rounded-3xl overflow-hidden shadow-inner bg-white"></div>
                                <div id="gr-reg" class="border border-slate-50 rounded-3xl overflow-hidden shadow-inner bg-white"></div>
                             </div>

                             <div id="admin-notice" class="hidden mt-8 p-4 bg-green-50 rounded-2xl border-2 border-green-200 text-center italic font-black text-[10px] text-green-800 uppercase underline decoration-green-400">
                                Acesso Administrativo Completo Ativo
                             </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <script>
            const _supa = supabase.createClient("VALOR_SURL", "VALOR_SKEY");
            const MASTER_EMAIL = "abielgm@icloud.com";

            // GERADOR DE LINHAS PARA A PLANILHA
            function addRow(initCount = 1) {
                const tbody = document.getElementById('table-body');
                for(let i=0; i<initCount; i++) {
                    const tr = document.createElement('tr');
                    tr.classList.add('border-b');
                    tr.innerHTML = `
                        <td class="border-r"><input type="date" class="grid-input date-input"></td>
                        <td class="border-r"><input type="number" step="0.1" class="grid-input tmin-input" placeholder="0.0"></td>
                        <td class="border-r"><input type="number" step="0.1" class="grid-input tmax-input" placeholder="0.0"></td>
                        <td><input type="number" step="0.1" class="grid-input var-input" placeholder="0.0"></td>
                    `;
                    tbody.appendChild(tr);
                }
            }
            addRow(6); // Começa com 6 linhas

            function toggleInputs() {
                const mode = document.getElementById('mode-data').value;
                document.getElementById('div-f').classList.toggle('hidden', mode === 'm');
                document.getElementById('div-m').classList.toggle('hidden', mode === 'f');
            }

            // AUTH BLINDADO
            async function handleAuth(type) {
                const email = document.getElementById('email').value;
                const password = document.getElementById('password').value;
                if(!email || !password) return alert("E-mail e senha são requeridos.");
                document.getElementById('loading').classList.remove('hidden');
                try {
                    let r = (type === 'login') ? await _supa.auth.signInWithPassword({email, password}) : await _supa.auth.signUp({email, password});
                    if(r.error) throw r.error;
                    location.reload();
                } catch(e) { alert("Autenticação: " + e.message); document.getElementById('loading').classList.add('hidden'); }
            }

            async function checkS() {
                const {data:{user}} = await _supa.auth.getUser();
                if(user) {
                    document.getElementById('login-section').classList.add('hidden');
                    document.getElementById('main-section').classList.remove('hidden');
                    document.getElementById('user-display').innerText = user.email;
                    if(user.email.toLowerCase() === MASTER_EMAIL.toLowerCase()) {
                        document.getElementById('admin-tag').classList.remove('hidden');
                        document.getElementById('admin-notice').classList.remove('hidden');
                    }
                }
            }
            checkS();
            async function logout() { 
                await _supa.auth.signOut(); 
                window.location.replace('/'); 
            }

            // PROCESSADOR DE CÁLCULO
            async function calcular() {
                document.getElementById('loading').classList.remove('hidden');
                const fd = new FormData();
                const mode = document.getElementById('mode-data').value;
                
                fd.append('analise', document.getElementById('analise_nome').value || "Analise_E_P");
                fd.append('tmin', document.getElementById('tmin').value);
                fd.append('tmax', document.getElementById('tmax').value);
                fd.append('passo', document.getElementById('passo').value);

                if(mode === 'f') {
                    const f = document.getElementById('arquivo').files[0];
                    if(!f) { alert("Importe seu arquivo científico!"); document.getElementById('loading').classList.add('hidden'); return; }
                    fd.append('file', f);
                } else {
                    // COLETA DADOS DA PLANILHA DIGITAL
                    let rows = [];
                    document.querySelectorAll('#table-body tr').forEach(tr => {
                        const date = tr.querySelector('.date-input').value;
                        const tmin = tr.querySelector('.tmin-input').value;
                        const tmax = tr.querySelector('.tmax-input').value;
                        const variable = tr.querySelector('.var-input').value;
                        if(date && tmin && tmax) {
                            rows.push(`${date},${tmin},${tmax},${variable}`);
                        }
                    });
                    if(rows.length < 3) { alert("A planilha precisa de pelo menos 3 linhas completas!"); document.getElementById('loading').classList.add('hidden'); return; }
                    fd.append('manual_data', rows.join('\\n'));
                }

                try {
                    const resp = await fetch('/analisar', {method: 'POST', body: fd});
                    const d = await resp.json();
                    
                    document.getElementById('result-view').classList.remove('hidden');
                    document.getElementById('view-name-display').innerText = "🔬 Result: " + d.nome;
                    document.getElementById('r-tb').innerText = d.best.t + "°C";
                    document.getElementById('r-r2').innerText = d.best.r2.toFixed(4);
                    document.getElementById('r-qme').innerText = d.best.qme.toFixed(7);

                    Plotly.newPlot('gr-qme', [{x: d.q.t, y: d.q.q, mode: 'lines+markers', line:{color:'black'}, marker:{color:'black', size:6}}], {
                        title: '<b>Curva Erro x Tb</b>', xaxis:{title:'Temperatura Testada (°C)'}, margin:{t:50, b:50}
                    });

                    Plotly.newPlot('gr-reg', [
                        {x: d.reg.x, y: d.reg.y, mode: 'markers', marker:{color:'gray', symbol:'circle-open'}, name:'Dados'},
                        {x: d.reg.x, y: d.reg.p, mode: 'lines', line:{color:'black', dash:'dot'}}
                    ], {
                        title: '<b>Regressão: NF x STa</b>', xaxis:{title:'Soma Térmica'}, showlegend:false, margin:{t:50, b:50}
                    });

                } catch(e) { 
                    alert("ALERTA CIENTÍFICO: Ocorreu erro na regressão. \\nCertifique-se que NF é cumulativa ou revise os limites Tb.");
                } finally { document.getElementById('loading').classList.add('hidden'); }
            }
        </script>
    </body>
    </html>
    """.replace("VALOR_SURL", S_URL).replace("VALOR_SKEY", S_KEY)
    return html_content

# --- BACKEND (O MOTOR DE INTEGRAÇÃO) ---
@app.post("/analisar")
async def analisar_dados(
    file: UploadFile = None, manual_data: str = Form(None),
    analise: str = Form(""), tmin: float = Form(0.0), tmax: float = Form(20.0), passo: float = Form(0.5)
):
    try:
        if file:
            content = await file.read()
            df = pd.read_csv(BytesIO(content), sep=None, engine='python') if file.filename.endswith('.csv') else pd.read_excel(BytesIO(content))
        else:
            df = pd.read_csv(StringIO(manual_data), names=['Data', 'Tmin', 'Tmax', 'NF'], header=None)
        
        # Saneamento de colunas para o motor.py
        df = rename_columns(df)
        df['Data'] = pd.to_datetime(df['Data'], errors='coerce')
        
        # Chama motor de agrometeorologia
        res = executar_calculo_tb(df, tmin, tmax, passo)
        
        mdf = pd.DataFrame(res['tabela_meteorologica'])
        melhor_t_float = float(res['melhor_resultado']['Temperatura (ºC)'])
        
        # Busca inteligente da coluna decimal mais próxima
        col_names = [float(c) for c in mdf.columns if c not in ['Dia', 'Mês', 'Ano', 'Tmin', 'Tmax', 'Tmed']]
        final_col = str(col_names[np.abs(np.array(col_names) - melhor_t_float).argmin()])
        
        idx = [i for i, v in enumerate(df['NF']) if not pd.isna(v)]
        
        return {
            "nome": analise,
            "best": {"t": res['melhor_resultado']['Temperatura (ºC)'], "r2": res['melhor_resultado']['R2'], "qme": res['melhor_resultado']['QME']},
            "q": {"t": [x['Temperatura (ºC)'] for x in res['tabela_erros']], "q": [x['QME'] for x in res['tabela_erros']]},
            "reg": {
                "x": [float(mdf.iloc[i][final_col]) for i in idx],
                "y": df['NF'].dropna().tolist(),
                "p": [float(mdf.iloc[i][final_col] * res['melhor_resultado']['Coef_Angular'] + res['melhor_resultado']['Intercepto']) for i in idx]
            }
        }
    except Exception as e:
        print(f"Error Trace: {str(e)}")
        raise HTTPException(status_code=500, detail="Scientific calculation failure.")
