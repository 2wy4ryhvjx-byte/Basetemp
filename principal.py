import os
import stripe
from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from fastapi.responses import HTMLResponse
import pandas as pd
from io import BytesIO
import json
from motor import executar_calculo_tb, rename_columns

app = FastAPI()

stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "")
EMAIL_ADMIN = "abielgm@icloud.com"

@app.get("/", response_class=HTMLResponse)
async def interface():
    s_url = os.getenv("SUPABASE_URL", "https://iuhtopexunirguxmjiey.supabase.co")
    s_key = os.getenv("SUPABASE_KEY", "")

    return f"""
    <!DOCTYPE html>
    <html lang="pt-br">
    <head>
        <meta charset="UTF-8"><title>EstimaTB Pro - Workstation</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <script src="https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2"></script>
        <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
        <style>
            .tab-active {{ border-bottom: 4px solid #16a34a; color: #16a34a; }}
            input[type=number]::-webkit-inner-spin-button {{ opacity: 1; }}
        </style>
    </head>
    <body class="bg-[#f8fafc] font-sans min-h-screen">
        
        <div class="max-w-6xl mx-auto p-4 md:p-8">
            
            <!-- SEÇÃO DE LOGIN -->
            <div id="login-section" class="max-w-md mx-auto bg-white p-10 rounded-[2.5rem] shadow-2xl mt-20 border border-slate-100 text-center">
                <h1 class="text-4xl font-black text-green-700 italic mb-8 italic">EstimaTB🌿</h1>
                <input type="email" id="email" placeholder="E-mail" class="w-full border-2 p-4 rounded-2xl mb-4 focus:border-green-600 outline-none">
                <input type="password" id="password" placeholder="Senha" class="w-full border-2 p-4 rounded-2xl mb-6 focus:border-green-600 outline-none">
                <button onclick="auth('login')" class="w-full bg-green-600 text-white py-4 rounded-2xl font-black text-lg shadow-lg hover:bg-green-700">ENTRAR</button>
                <button onclick="auth('signup')" class="mt-4 text-green-600 text-xs font-bold uppercase tracking-widest">Novo Cadastro</button>
            </div>

            <!-- ÁREA PRINCIPAL -->
            <div id="main-section" class="hidden animate-fade-in">
                <!-- Header Status -->
                <div class="bg-white p-6 rounded-[2rem] shadow-sm mb-6 flex justify-between items-center border border-slate-100">
                    <div>
                        <span class="text-[10px] font-black text-slate-400 uppercase tracking-widest block">Ambiente de Pesquisa</span>
                        <span id="user-display" class="font-bold text-slate-700"></span>
                    </div>
                    <div id="admin-badge" class="hidden px-4 py-1 bg-green-50 text-green-700 rounded-full font-black text-[10px] border border-green-200 uppercase">Administrador Master</div>
                    <button onclick="logout()" class="text-slate-400 hover:text-red-500 font-bold text-xs uppercase">Sair</button>
                </div>

                <!-- Painel de Trabalho -->
                <div class="grid grid-cols-1 lg:grid-cols-12 gap-6">
                    
                    <div class="lg:col-span-4 space-y-6">
                        <!-- Nome da Análise e Inputs -->
                        <div class="bg-white p-6 rounded-[2rem] shadow-xl border border-slate-100">
                            <h3 class="font-black text-slate-800 text-xs uppercase mb-4 flex items-center"><i class="fas fa-microscope mr-2 text-green-600"></i>Configurar Análise</h3>
                            
                            <input type="text" id="analise_nome" placeholder="Nome da Análise (ex: Soja Época 1)" class="w-full border-2 p-3 rounded-xl mb-4 text-sm outline-none focus:border-green-600">
                            
                            <!-- Tabs de Entrada -->
                            <div class="flex border-b mb-4">
                                <button id="tabFile" onclick="switchTab('file')" class="flex-1 py-2 text-xs font-bold tab-active">Upload Arquivo</button>
                                <button id="tabManual" onclick="switchTab('manual')" class="flex-1 py-2 text-xs font-bold text-slate-400">Entrada Manual</button>
                            </div>

                            <div id="input_file_container">
                                <input type="file" id="arquivo" class="block w-full text-[10px] border-2 border-dashed p-4 rounded-xl cursor-pointer bg-slate-50 mb-4">
                            </div>

                            <div id="input_manual_container" class="hidden">
                                <p class="text-[10px] text-slate-500 mb-2 italic">Preencha no padrão: Data, Tmin, Tmax, NF</p>
                                <textarea id="manual_data" placeholder="2023-10-01, 15.5, 28.4, 2" class="w-full border-2 p-3 rounded-xl h-32 text-xs font-mono outline-none" rows="5"></textarea>
                            </div>

                            <!-- Configurações Avançadas -->
                            <details class="mb-6 group">
                                <summary class="list-none cursor-pointer flex justify-between items-center text-[10px] font-black text-slate-500 hover:text-green-600 uppercase tracking-widest bg-slate-50 p-2 rounded-lg">
                                    <span>Configurações Avançadas</span>
                                    <i class="fas fa-chevron-down transition group-open:rotate-180"></i>
                                </summary>
                                <div class="p-4 bg-slate-50 rounded-b-lg border-t space-y-3">
                                    <div class="flex justify-between items-center">
                                        <label class="text-[10px] font-bold">Tb Mínima:</label>
                                        <input type="number" id="tb_min" value="0.0" step="0.5" class="w-20 border rounded p-1 text-center font-bold">
                                    </div>
                                    <div class="flex justify-between items-center">
                                        <label class="text-[10px] font-bold">Tb Máxima:</label>
                                        <input type="number" id="tb_max" value="20.0" step="0.5" class="w-20 border rounded p-1 text-center font-bold">
                                    </div>
                                    <div class="flex justify-between items-center">
                                        <label class="text-[10px] font-bold">Passo (0.1 a 0.9):</label>
                                        <input type="number" id="passo" value="0.5" min="0.1" max="0.9" step="0.1" class="w-20 border rounded p-1 text-center font-bold">
                                    </div>
                                </div>
                            </details>

                            <button id="btnCalc" onclick="calcular()" class="w-full bg-green-600 text-white py-5 rounded-[1.5rem] font-black text-xl shadow-lg hover:bg-green-700 transition-all uppercase tracking-tighter">
                                Analisar Dados
                            </button>
                        </div>
                    </div>

                    <div id="results_area" class="lg:col-span-8 space-y-6 hidden">
                        <!-- Nome e Métricas -->
                        <div class="bg-white p-6 rounded-[2rem] shadow-xl">
                             <h2 class="text-xl font-black text-slate-800 mb-6 italic underline decoration-green-500" id="display_nome_analise"></h2>
                             <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
                                <div class="bg-slate-50 p-6 rounded-3xl border-b-4 border-green-600 text-center">
                                    <span class="text-[9px] font-black text-slate-400 uppercase italic">Temp. Basal (Tb)</span>
                                    <p id="res_tb" class="text-3xl font-black text-green-700 mt-2">--</p>
                                </div>
                                <div class="bg-slate-50 p-6 rounded-3xl border-b-4 border-blue-600 text-center">
                                    <span class="text-[9px] font-black text-slate-400 uppercase italic">Ajuste (R²)</span>
                                    <p id="res_r2" class="text-3xl font-black text-blue-700 mt-2">--</p>
                                </div>
                                <div class="bg-slate-50 p-6 rounded-3xl border-b-4 border-slate-600 text-center">
                                    <span class="text-[9px] font-black text-slate-400 uppercase italic">Erro (QME)</span>
                                    <p id="res_qme" class="text-lg font-black text-slate-600 mt-3 tracking-tighter">--</p>
                                </div>
                             </div>
                        </div>

                        <!-- Gráficos e Tabela -->
                        <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
                            <div class="bg-white p-4 rounded-3xl shadow-lg border border-slate-100" id="graph-qme"></div>
                            <div class="bg-white p-4 rounded-3xl shadow-lg border border-slate-100" id="graph-reg"></div>
                        </div>

                        <div class="bg-white p-6 rounded-3xl shadow-lg border border-slate-100">
                             <h3 class="text-xs font-black uppercase mb-4 text-slate-500 italic">Pré-visualização da Base</h3>
                             <div id="table_preview" class="overflow-auto max-h-48 text-[10px] font-mono"></div>
                        </div>
                    </div>

                </div>
            </div>
        </div>

        <script>
            const _supabase = supabase.createClient("{s_url}", "{s_key}");
            const ADMIN_EMAIL = "{EMAIL_ADMIN}".toLowerCase();
            let currentTab = 'file';

            function switchTab(t) {{
                currentTab = t;
                document.getElementById('tabFile').classList.toggle('tab-active', t==='file');
                document.getElementById('tabManual').classList.toggle('tab-active', t==='manual');
                document.getElementById('input_file_container').classList.toggle('hidden', t!=='file');
                document.getElementById('input_manual_container').classList.toggle('hidden', t!=='manual');
            }}

            async function auth(type) {{
                const e = document.getElementById('email').value;
                const p = document.getElementById('password').value;
                if(type==='login') await _supabase.auth.signInWithPassword({{email:e, password:p}});
                else await _supabase.auth.signUp({{email:e, password:p}});
                location.reload();
            }}

            async function checkUser() {{
                const {{data:{{user}}}} = await _supabase.auth.getUser();
                if(user) {{
                    document.getElementById('login-section').classList.add('hidden');
                    document.getElementById('main-section').classList.remove('hidden');
                    document.getElementById('user-display').innerText = user.email.toLowerCase();
                    if(user.email.toLowerCase() === ADMIN_EMAIL) document.getElementById('admin-badge').classList.remove('hidden');
                }}
            }}
            checkUser();
            function logout() {{ _supabase.auth.signOut(); location.reload(); }}

            async function calcular() {{
                const btn = document.getElementById('btnCalc');
                const analise_nome = document.getElementById('analise_nome').value || "Nova Análise";
                const file = document.getElementById('arquivo').files[0];
                const manual = document.getElementById('manual_data').value;
                const tmin = document.getElementById('tb_min').value;
                const tmax = document.getElementById('tb_max').value;
                const passo = document.getElementById('passo').value;

                if(currentTab==='file' && !file) return alert("Selecione o arquivo meteorológico!");
                
                btn.innerText = "SINCRO MODELO...";
                btn.disabled = true;

                const fd = new FormData();
                if(currentTab === 'file') fd.append('file', file);
                else fd.append('manual_data', manual);
                
                fd.append('tmin', tmin);
                fd.append('tmax', tmax);
                fd.append('passo', passo);

                try {{
                    const response = await fetch('/analisar', {{ method: 'POST', body: fd }});
                    const d = await response.json();

                    document.getElementById('results_area').classList.remove('hidden');
                    document.getElementById('display_nome_analise').innerText = "🔬 Result: " + analise_nome;
                    document.getElementById('res_tb').innerText = d.best_result.temperatura + " °C";
                    document.getElementById('res_r2').innerText = d.best_result.r2.toFixed(4);
                    document.getElementById('res_qme').innerText = d.best_result.qme.toFixed(6);

                    // Tabela
                    let htmlTable = '<table class="w-full text-left"><thead><tr class="bg-slate-50"><th>Data</th><th>Tmin</th><th>Tmax</th><th>NF</th></tr></thead><tbody>';
                    d.preview.forEach(row => {{
                        htmlTable += `<tr class="border-b"><td>${{row.Data}}</td><td>${{row.Tmin}}</td><td>${{row.Tmax}}</td><td>${{row.NF}}</td></tr>`;
                    }});
                    document.getElementById('table_preview').innerHTML = htmlTable + "</tbody></table>";

                    // Graf QME
                    Plotly.newPlot('graph-qme', [{{
                        x: d.qme_data.temp, y: d.qme_data.qme,
                        type: 'scatter', mode: 'lines+markers', marker: {{color:'black'}}, line: {{color:'black'}}
                    }}], {{ title: 'QME vs Tb', xaxis:{{title:'°C'}}, yaxis:{{title:'Erro'}}, height: 350 }});

                    // Graf Regressao
                    Plotly.newPlot('graph-reg', [
                        {{ x: d.reg.sta, y: d.reg.nf, mode: 'markers', marker: {{color:'gray'}} }},
                        {{ x: d.reg.sta, y: d.reg.predict, mode: 'lines', line: {{color:'black', dash:'dot'}} }}
                    ], {{ title: 'Regressão / Intercepto', xaxis:{{title:'STa'}}, yaxis:{{title:'Folhas'}}, height: 350, showlegend:false }});

                }} catch(e) {{
                    alert("Dados inválidos ou formato incorreto. Verifique as colunas (Data, Tmin, Tmax, NF).");
                }} finally {{
                    btn.innerText = "Analisar Dados"; btn.disabled = false;
                }}
            }}
        </script>
    </body>
    </html>
    """

@app.post("/analisar")
async def analisar_dados(
    file: UploadFile = None, 
    manual_data: str = Form(None),
    tmin: float = Form(0.0),
    tmax: float = Form(20.0),
    passo: float = Form(0.5)
):
    try:
        # Define qual fonte de dados usar
        if file:
            content = await file.read()
            if file.filename.endswith('.csv'):
                df = pd.read_csv(BytesIO(content), sep=None, engine='python')
            else:
                df = pd.read_excel(BytesIO(content))
        elif manual_data:
            # Converte texto CSV em DataFrame
            from io import StringIO
            data = StringIO(manual_data)
            df = pd.read_csv(data, names=['Data', 'Tmin', 'Tmax', 'NF'], header=None)
        else:
            raise HTTPException(status_code=400, detail="Sem dados.")

        df = rename_columns(df)
        df['Data'] = pd.to_datetime(df['Data'], errors='coerce')
        
        # O Motor
        res = executar_calculo_tb(df, tmin, tmax, passo)
        
        # Mapeamento para gráficos e retorno
        met_df = pd.DataFrame(res['tabela_meteorologica'])
        best_tb_str = str(round(res['melhor_resultado']['Temperatura (ºC)'], 2))
        idx_nf = [i for i, v in enumerate(df['NF']) if not pd.isna(v)]

        return {
            "best_result": {
                "temperatura": res['melhor_resultado']['Temperatura (ºC)'],
                "r2": res['melhor_resultado']['R2'],
                "qme": res['melhor_resultado']['QME']
            },
            "preview": df.head(10).astype(str).to_dict(orient="records"),
            "qme_data": {
                "temp": [x['Temperatura (ºC)'] for x in res['tabela_erros']],
                "qme": [x['QME'] for x in res['tabela_erros']]
            },
            "reg": {
                "sta": [met_df.iloc[i][best_tb_str] for i in idx_nf],
                "nf": df['NF'].dropna().tolist(),
                "predict": [
                    met_df.iloc[i][best_tb_str] * res['melhor_resultado']['Coef_Angular'] + res['melhor_resultado']['Intercepto'] 
                    for i in idx_nf
                ]
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
