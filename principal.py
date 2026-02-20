import os
import stripe
from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from fastapi.responses import HTMLResponse
import pandas as pd
from io import BytesIO
from motor import executar_calculo_tb, rename_columns

app = FastAPI()

# Configurações do ambiente
stripe_api_key = os.getenv("STRIPE_SECRET_KEY", "")
EMAIL_ADMIN = "abielgm@icloud.com"

@app.get("/", response_class=HTMLResponse)
async def interface():
    # Passamos as chaves para o frontend. 
    # Usando .get com fallback para strings vazias para não quebrar o f-string
    s_url = os.getenv("SUPABASE_URL", "")
    s_key = os.getenv("SUPABASE_KEY", "")

    return f"""
    <!DOCTYPE html>
    <html lang="pt-br">
    <head>
        <meta charset="UTF-8"><title>EstimaTB Pro</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <script src="https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2"></script>
        <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
    </head>
    <body class="bg-slate-50 font-sans min-h-screen">
        <div id="loader" class="hidden fixed inset-0 bg-white bg-opacity-80 flex items-center justify-center z-50">
            <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-green-600"></div>
        </div>

        <div class="max-w-6xl mx-auto p-4 md:p-10">
            <!-- LOGIN SECTION -->
            <div id="login-section" class="max-w-md mx-auto bg-white p-8 rounded-[2rem] shadow-2xl mt-10">
                <h1 class="text-3xl font-black text-green-700 text-center mb-8 italic">EstimaTB 🌿</h1>
                <div class="space-y-4">
                    <input type="email" id="email" placeholder="E-mail" class="w-full border p-3 rounded-xl outline-none focus:ring-2 focus:ring-green-500">
                    <input type="password" id="password" placeholder="Senha" class="w-full border p-3 rounded-xl outline-none focus:ring-2 focus:ring-green-500">
                    <button onclick="handleAuth('login')" id="btnLogin" class="w-full bg-green-600 text-white py-3 rounded-xl font-bold">Entrar</button>
                    <button onclick="handleAuth('signup')" class="w-full text-green-600 text-xs font-bold uppercase">Cadastrar Novo Usuário</button>
                </div>
                <p id="auth-error" class="text-red-500 text-xs mt-4 text-center font-bold"></p>
            </div>

            <!-- WORKSTATION (HIDDEN BY DEFAULT) -->
            <div id="main-section" class="hidden">
                <div class="flex justify-between items-center bg-white p-6 rounded-3xl shadow-sm border mb-6">
                    <p class="font-bold text-gray-600">Olá, <span id="user-display" class="text-green-600"></span></p>
                    <button onclick="logout()" class="bg-red-50 text-red-500 px-4 py-1 rounded-full text-xs font-bold">SAIR</button>
                </div>

                <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
                    <div class="bg-white p-6 rounded-[2rem] shadow-lg">
                        <input type="text" id="analise_nome" placeholder="Nome da Análise" class="w-full border p-3 rounded-xl mb-4 text-sm">
                        
                        <label class="text-[10px] font-black text-gray-400 uppercase tracking-widest mb-2 block">Fonte de Dados</label>
                        <select id="data-source" onchange="toggleSource()" class="w-full border p-3 rounded-xl mb-4 text-sm bg-gray-50">
                            <option value="file">Arquivo (Excel/CSV)</option>
                            <option value="manual">Entrada Manual</option>
                        </select>

                        <div id="src-file">
                            <input type="file" id="arquivo" class="block w-full text-xs border-2 border-dashed p-4 rounded-xl mb-4">
                        </div>
                        <div id="src-manual" class="hidden">
                            <textarea id="manual_data" placeholder="Data, Tmin, Tmax, NF (uma por linha)" class="w-full border p-3 rounded-xl h-32 text-xs font-mono"></textarea>
                        </div>

                        <div class="bg-gray-50 p-4 rounded-2xl mb-6">
                             <p class="text-[10px] font-bold text-gray-400 mb-3 uppercase">Configurações Avançadas</p>
                             <div class="grid grid-cols-3 gap-2">
                                <div><label class="text-[9px]">Mín</label><input type="number" id="tmin" value="0" class="w-full border p-1 rounded"></div>
                                <div><label class="text-[9px]">Máx</label><input type="number" id="tmax" value="20" class="w-full border p-1 rounded"></div>
                                <div><label class="text-[9px]">Passo</label><input type="number" id="passo" value="0.5" step="0.1" class="w-full border p-1 rounded"></div>
                             </div>
                        </div>

                        <button id="btnCalc" onclick="calcular()" class="w-full bg-green-600 text-white py-4 rounded-2xl font-black shadow-lg">ANALISAR</button>
                    </div>

                    <div id="results-display" class="lg:col-span-2 space-y-6 hidden">
                        <div class="grid grid-cols-3 gap-4">
                            <div class="bg-white p-6 rounded-3xl shadow-md border-b-4 border-green-500 text-center"><p class="text-[9px] font-bold text-gray-400">Tb</p><p id="res-tb" class="text-3xl font-black text-green-600"></p></div>
                            <div class="bg-white p-6 rounded-3xl shadow-md border-b-4 border-blue-500 text-center"><p class="text-[9px] font-bold text-gray-400">R²</p><p id="res-r2" class="text-3xl font-black text-blue-600"></p></div>
                            <div class="bg-white p-6 rounded-3xl shadow-md border-b-4 border-gray-500 text-center"><p class="text-[9px] font-bold text-gray-400">QME</p><p id="res-qme" class="text-xl font-bold text-gray-700"></p></div>
                        </div>
                        <div id="chart-qme" class="bg-white p-4 rounded-3xl shadow-lg h-64"></div>
                        <div id="chart-reg" class="bg-white p-4 rounded-3xl shadow-lg h-64"></div>
                        <div id="table-preview" class="bg-white p-6 rounded-3xl shadow-lg overflow-auto max-h-40 text-[10px]"></div>
                    </div>
                </div>
            </div>
        </div>

        <script>
            // Conexão segura com Supabase
            const SUPABASE_URL = "{s_url}";
            const SUPABASE_KEY = "{s_key}";
            const ADMIN_EMAIL = "{EMAIL_ADMIN}";

            if(!SUPABASE_URL || !SUPABASE_KEY) alert("Erro: Chaves não detectadas.");

            const _supabase = supabase.createClient(SUPABASE_URL, SUPABASE_KEY);

            function showLoader(v) {{ document.getElementById('loader').classList.toggle('hidden', !v); }}

            async function handleAuth(type) {{
                const email = document.getElementById('email').value;
                const password = document.getElementById('password').value;
                const errorDisplay = document.getElementById('auth-error');
                if(!email || !password) return alert("E-mail/Senha obrigatórios");

                showLoader(true);
                let result;
                if(type === 'login') result = await _supabase.auth.signInWithPassword({{ email, password }});
                else result = await _supabase.auth.signUp({{ email, password }});
                
                if(result.error) {{
                    errorDisplay.innerText = "Erro: " + result.error.message;
                    showLoader(false);
                }} else {{
                    location.reload();
                }}
            }}

            async function logout() {{ await _supabase.auth.signOut(); location.reload(); }}

            async function checkSession() {{
                const {{ data: {{ user }} }} = await _supabase.auth.getUser();
                if(user) {{
                    document.getElementById('login-section').classList.add('hidden');
                    document.getElementById('main-section').classList.remove('hidden');
                    document.getElementById('user-display').innerText = user.email;
                    // Lógica admin seria injetada aqui
                }}
            }}
            checkSession();

            function toggleSource() {{
                const src = document.getElementById('data-source').value;
                document.getElementById('src-file').classList.toggle('hidden', src !== 'file');
                document.getElementById('src-manual').classList.toggle('hidden', src !== 'manual');
            }}

            async function calcular() {{
                const btn = document.getElementById('btnCalc');
                const source = document.getElementById('data-source').value;
                const file = document.getElementById('arquivo').files[0];
                const manual = document.getElementById('manual_data').value;
                const tmin = document.getElementById('tmin').value;
                const tmax = document.getElementById('tmax').value;
                const passo = document.getElementById('passo').value;

                if(source==='file' && !file) return alert("Escolha um arquivo!");
                
                showLoader(true);
                const fd = new FormData();
                if(source==='file') fd.append('file', file);
                else fd.append('manual_data', manual);
                fd.append('tmin', tmin); fd.append('tmax', tmax); fd.append('passo', passo);

                try {{
                    const response = await fetch('/analisar', {{ method: 'POST', body: fd }});
                    const d = await response.json();

                    document.getElementById('results-display').classList.remove('hidden');
                    document.getElementById('res-tb').innerText = d.best_result.temperatura + "°C";
                    document.getElementById('res-r2').innerText = d.best_result.r2.toFixed(4);
                    document.getElementById('res-qme').innerText = d.best_result.qme.toFixed(6);

                    // Renderização de Gráficos (Plotly)
                    Plotly.newPlot('chart-qme', [{{ x: d.qme_data.temp, y: d.qme_data.qme, type:'scatter', marker:{{color:'black'}} }}], {{title:'Curva de QME', margin:{{t:30}}}});
                    Plotly.newPlot('chart-reg', [{{ x: d.reg.sta, y: d.reg.nf, mode:'markers', marker:{{color:'gray'}} }}, {{x: d.reg.sta, y: d.reg.predict, mode:'lines', line:{{color:'black'}}}}], {{title:'Reta de Regressão', showlegend:false, margin:{{t:30}}}});

                    let table = '<table class="w-full text-left"><thead><tr class="bg-gray-50"><th>Data</th><th>Tmin</th><th>Tmax</th><th>NF</th></tr></thead><tbody>';
                    d.preview.forEach(row => table += `<tr><td>${{row.Data}}</td><td>${{row.Tmin}}</td><td>${{row.Tmax}}</td><td>${{row.NF}}</td></tr>`);
                    document.getElementById('table-preview').innerHTML = table + '</tbody></table>';

                }} catch(e) {{
                    alert("Erro no processamento. Verifique os dados.");
                }} finally {{
                    showLoader(false);
                }}
            }}
        </script>
    </body>
    </html>
    """

# Funções Analisar e motor devem ser as mesmas enviadas anteriormente.
