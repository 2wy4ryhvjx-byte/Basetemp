import os
import stripe
import pandas as pd
from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from fastapi.responses import HTMLResponse
from io import BytesIO, StringIO
from motor import executar_calculo_tb, rename_columns

app = FastAPI()

# Configurações do ambiente (Render)
stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "")
EMAIL_ADMIN = "abielgm@icloud.com"

@app.get("/", response_class=HTMLResponse)
async def interface():
    # Coletamos as chaves para injetar no JavaScript
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
    <body class="bg-slate-50 font-sans min-h-screen text-slate-900">
        
        <div id="loading" class="hidden fixed inset-0 bg-white/80 flex items-center justify-center z-50 flex-col">
            <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-green-700 mb-4"></div>
            <p class="font-black text-green-800 italic animate-pulse">SINCRO PROCESSANDO...</p>
        </div>

        <div class="max-w-6xl mx-auto p-4 md:p-8">
            <!-- TELA DE LOGIN -->
            <div id="login-section" class="max-w-md mx-auto bg-white p-10 rounded-[3rem] shadow-2xl mt-12 border border-slate-200 text-center animate-in fade-in duration-500">
                <h1 class="text-4xl font-black text-green-700 italic mb-2 tracking-tighter">EstimaTB🌿</h1>
                <p class="text-[10px] font-black text-slate-300 uppercase tracking-widest mb-8 italic">Agrometeorology Laboratory</p>
                
                <div class="space-y-4">
                    <input type="email" id="email" placeholder="E-mail Acadêmico" class="w-full bg-slate-50 border-2 border-slate-100 p-4 rounded-2xl outline-none focus:border-green-600">
                    <input type="password" id="password" placeholder="Senha" class="w-full bg-slate-50 border-2 border-slate-100 p-4 rounded-2xl outline-none focus:border-green-600">
                    <button onclick="handleAuth('login')" id="btnLogin" class="w-full bg-green-600 text-white py-4 rounded-2xl font-black shadow-lg hover:bg-green-700 active:scale-95 transition-all uppercase tracking-tighter">Entrar</button>
                    <button onclick="handleAuth('signup')" class="text-green-700 font-black text-[10px] uppercase mt-2 tracking-widest hover:underline">Cadastrar Nova Conta</button>
                </div>
            </div>

            <!-- ÁREA DE TRABALHO -->
            <div id="main-section" class="hidden">
                <div class="flex flex-col md:flex-row justify-between items-center bg-white p-6 rounded-3xl shadow-sm border border-slate-200 mb-6 gap-4">
                    <p class="font-bold text-slate-500 text-sm italic">User: <span id="user-display" class="text-green-700 font-black not-italic ml-1"></span></p>
                    <div id="admin-tag" class="hidden bg-green-100 text-green-700 text-[10px] font-black px-4 py-1 rounded-full italic border border-green-200 uppercase">⭐ Administrador Master</div>
                    <button onclick="logout()" class="text-slate-400 font-black text-[10px] hover:text-red-500 uppercase tracking-widest">Sair do Sistema</button>
                </div>

                <div class="grid grid-cols-1 lg:grid-cols-12 gap-8">
                    <!-- Configurações Side -->
                    <div class="lg:col-span-4 space-y-6">
                        <div class="bg-white p-8 rounded-[2.5rem] shadow-xl border border-slate-100">
                            <h3 class="font-black text-slate-800 text-xs uppercase mb-6 flex items-center italic underline decoration-green-500 underline-offset-4">Configurações de Modelagem</h3>
                            
                            <label class="text-[10px] font-black text-slate-400 uppercase ml-2 mb-1 block italic">Nome do Experimento</label>
                            <input type="text" id="analise_nome" placeholder="ex: Lavras - Milho Safrinha" class="w-full border-2 p-4 rounded-2xl mb-6 bg-slate-50 text-sm focus:border-green-600 outline-none">

                            <label class="text-[10px] font-black text-slate-400 uppercase ml-2 mb-2 block italic">Origem dos Dados Científicos</label>
                            <div class="flex gap-2 p-1 bg-slate-100 rounded-2xl mb-4">
                                <button onclick="setTab('file')" id="btnTabFile" class="flex-1 py-3 text-xs font-black rounded-xl bg-white shadow-sm text-green-700 transition-all uppercase italic">Arquivo</button>
                                <button onclick="setTab('manual')" id="btnTabManual" class="flex-1 py-3 text-xs font-black text-slate-400 rounded-xl transition-all uppercase italic tracking-tighter">Entrada Manual</button>
                            </div>

                            <div id="divFile"><input type="file" id="arquivo" class="block w-full text-[10px] border-2 border-dashed border-slate-200 p-6 rounded-2xl bg-slate-50 mb-6"></div>
                            <div id="divManual" class="hidden"><textarea id="manual_data" placeholder="Data, Tmin, Tmax, NF&#10;2024-01-01, 10.5, 25.8, 1&#10;2024-01-05, 12.0, 26.2, 2" class="w-full border-2 p-4 rounded-2xl bg-slate-50 text-xs font-mono mb-6 h-40 outline-none"></textarea></div>

                            <div class="bg-slate-50 p-6 rounded-[1.5rem] border border-slate-100 mb-8">
                                <p class="text-[9px] font-black text-slate-400 uppercase tracking-widest mb-4 italic text-center underline">Avançado: Parâmetros de Referência</p>
                                <div class="grid grid-cols-3 gap-3">
                                    <div class="text-center"><label class="text-[9px] font-bold block mb-1 uppercase">Tb Mín</label><input type="number" id="tmin" value="0.0" class="w-full border text-center p-2 rounded-xl font-bold"></div>
                                    <div class="text-center"><label class="text-[9px] font-bold block mb-1 uppercase">Tb Máx</label><input type="number" id="tmax" value="20.0" class="w-full border text-center p-2 rounded-xl font-bold"></div>
                                    <div class="text-center"><label class="text-[9px] font-bold block mb-1 uppercase">Passo</label><input type="number" id="passo" value="0.5" step="0.1" class="w-full border text-center p-2 rounded-xl font-bold text-green-700"></div>
                                </div>
                            </div>

                            <button onclick="calcular()" id="btnCalc" class="w-full bg-green-600 text-white py-5 rounded-[1.5rem] font-black text-xl shadow-xl hover:scale-105 transition-all uppercase tracking-tighter">Calcular Tb</button>
                        </div>
                    </div>

                    <!-- Resultados Principal -->
                    <div id="result-view" class="lg:col-span-8 hidden space-y-6">
                        <div class="bg-white p-8 rounded-[3rem] shadow-2xl border-t-[10px] border-slate-900">
                             <div class="flex justify-between items-center border-b pb-6 mb-8">
                                <h2 id="view-name" class="text-2xl font-black italic tracking-tighter text-slate-800"></h2>
                                <span class="bg-slate-900 text-white px-3 py-1 rounded text-[10px] font-bold uppercase tracking-widest">Processamento Concluído</span>
                             </div>
                             
                             <div class="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
                                <div class="bg-slate-50 p-6 rounded-3xl border-2 border-slate-100 text-center">
                                    <span class="text-[9px] font-black text-slate-400 uppercase italic block mb-1">Temperatura Basal</span>
                                    <p id="res-tb" class="text-4xl font-black text-slate-900 mt-2 font-mono tracking-tighter"></p>
                                </div>
                                <div class="bg-slate-50 p-6 rounded-3xl border-2 border-slate-100 text-center">
                                    <span class="text-[9px] font-black text-slate-400 uppercase italic block mb-1">Coef. de Precisão (R²)</span>
                                    <p id="res-r2" class="text-4xl font-black text-slate-900 mt-2 font-mono tracking-tighter"></p>
                                </div>
                                <div class="bg-slate-50 p-6 rounded-3xl border-2 border-slate-100 text-center">
                                    <span class="text-[9px] font-black text-slate-400 uppercase italic block mb-1">Mínimo QME</span>
                                    <p id="res-qme" class="text-xl font-black text-slate-900 mt-3 font-mono"></p>
                                </div>
                             </div>

                             <!-- Tabelas e Gráficos -->
                             <div class="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
                                <div class="bg-white p-2 border-2 rounded-3xl border-slate-50 shadow-inner h-[320px]" id="qme-chart"></div>
                                <div class="bg-white p-2 border-2 rounded-3xl border-slate-50 shadow-inner h-[320px]" id="reg-chart"></div>
                             </div>

                             <div class="bg-white border-2 border-slate-100 rounded-3xl overflow-hidden p-6 shadow-sm">
                                <h3 class="text-[10px] font-black uppercase text-slate-400 italic mb-4">Amostra da Base de Dados Carregada</h3>
                                <div id="table-view" class="overflow-auto max-h-44 text-[10px] font-mono leading-tight"></div>
                             </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <script>
            // INJEÇÃO DAS VARIÁVEIS (Python -> JS)
            const SUP_URL = "{s_url}";
            const SUP_KEY = "{s_key}";
            const ADMIN_EMAIL = "{EMAIL_ADMIN}";

            if(!SUP_URL || !SUP_KEY) alert("CONFIGURAÇÃO: As variáveis SUPABASE_URL ou SUPABASE_KEY não estão configuradas no painel do Render!");

            const _supabase = supabase.createClient(SUP_URL, SUP_KEY);
            let tab = 'file';

            function setTab(t) {{
                tab = t;
                document.getElementById('btnTabFile').classList.toggle('bg-white', t==='file');
                document.getElementById('btnTabFile').classList.toggle('shadow-sm', t==='file');
                document.getElementById('btnTabFile').classList.toggle('text-green-700', t==='file');
                document.getElementById('btnTabManual').classList.toggle('bg-white', t==='manual');
                document.getElementById('btnTabManual').classList.toggle('shadow-sm', t==='manual');
                document.getElementById('btnTabManual').classList.toggle('text-green-700', t==='manual');
                document.getElementById('divFile').classList.toggle('hidden', t!=='file');
                document.getElementById('divManual').classList.toggle('hidden', t!=='manual');
            }}

            async function handleAuth(type) {{
                const e = document.getElementById('email').value;
                const p = document.getElementById('password').value;
                if(!e || !p) return alert("E-mail e senha são obrigatórios para acesso ao Lab.");
                
                document.getElementById('loading').classList.remove('hidden');
                
                let res;
                if(type === 'login') res = await _supabase.auth.signInWithPassword({{ email: e, password: p }});
                else res = await _supabase.auth.signUp({{ email: e, password: p }});

                if(res.error) {{
                    document.getElementById('loading').classList.add('hidden');
                    alert("ALERTA SUPABASE: " + res.error.message);
                }} else {{
                    location.reload();
                }}
            }}

            async function checkSession() {{
                const {{ data: {{ user }} }} = await _supabase.auth.getUser();
                if(user) {{
                    document.getElementById('login-section').classList.add('hidden');
                    document.getElementById('main-section').classList.remove('hidden');
                    document.getElementById('user-display').innerText = user.email.toLowerCase();
                    if(user.email.toLowerCase() === ADMIN_EMAIL.toLowerCase()) {{
                        document.getElementById('admin-tag').classList.remove('hidden');
                    }}
                }}
            }}
            checkSession();
            function logout() {{ _supabase.auth.signOut(); location.reload(); }}

            async function calcular() {{
                const file = document.getElementById('arquivo').files[0];
                const manual = document.getElementById('manual_data').value;
                const btn = document.getElementById('btnCalc');
                
                document.getElementById('loading').classList.remove('hidden');

                const fd = new FormData();
                fd.append('analise', document.getElementById('analise_nome').value || "Indefinida");
                fd.append('tmin', document.getElementById('tmin').value);
                fd.append('tmax', document.getElementById('tmax').value);
                fd.append('passo', document.getElementById('passo').value);

                if(tab === 'file' && !file) {{ alert("Selecione um arquivo!"); document.getElementById('loading').classList.add('hidden'); return; }}
                if(tab === 'file') fd.append('file', file); else fd.append('manual_data', manual);

                try {{
                    const resp = await fetch('/analisar', {{ method: 'POST', body: fd }});
                    const d = await resp.json();

                    document.getElementById('result-view').classList.remove('hidden');
                    document.getElementById('view-name').innerText = "🔬 Result: " + d.nome;
                    document.getElementById('res-tb').innerText = d.best.temp + " °C";
                    document.getElementById('res-r2').innerText = d.best.r2.toFixed(4);
                    document.getElementById('res-qme').innerText = d.best.qme.toFixed(6);

                    // Tabela
                    let html = '<table class="w-full text-left"><thead><tr class="bg-slate-50 italic"><th>Data</th><th>Tmin</th><th>Tmax</th><th>NF</th></tr></thead><tbody>';
                    d.preview.forEach(row => {{ html += `<tr class="border-b"><td>${{row.Data}}</td><td>${{row.Tmin}}</td><td>${{row.Tmax}}</td><td>${{row.NF}}</td></tr>`; }});
                    document.getElementById('table-view').innerHTML = html + "</tbody></table>";

                    // Grafs Plotly em P&B
                    Plotly.newPlot('qme-chart', [{{ x: d.qme_data.t, y: d.qme_data.q, type: 'scatter', mode: 'lines+markers', marker: {{color:'black'}}, line:{{color:'black', width:2}} }}], {{ title: '<b>Curva Mínimo QME</b>', xaxis:{{title:'Temperatura (°C)', gridcolor:'#eee'}}, yaxis:{{title:'QME', gridcolor:'#eee'}}, margin:{{t:40}} }});
                    Plotly.newPlot('reg-chart', [
                        {{ x: d.reg.sta, y: d.reg.nf, mode:'markers', marker:{{color:'gray', symbol:'circle-open'}}, name:'Dados' }},
                        {{ x: d.reg.sta, y: d.reg.y, mode:'lines', line:{{color:'black', dash:'dot'}}, name:'Modelo' }}
                    ], {{ title: '<b>Regressão Lineo-Base</b>', xaxis:{{title:'STa (Acumulada)', gridcolor:'#eee'}}, yaxis:{{title:'Folhas (NF)', gridcolor:'#eee'}}, showlegend:false, margin:{{t:40}} }});

                }} catch(e) {{ alert("ERRO DE PROCESSAMENTO: Verifique a formatação do seu arquivo CSV/XLSX."); }}
                finally {{ document.getElementById('loading').classList.add('hidden'); }}
            }}
        </script>
    </body>
    </html>
    """

# --- BACKEND FASTAPI ---
@app.post("/analisar")
async def analisar(
    file: UploadFile = None, 
    manual_data: str = Form(None),
    analise: str = Form("Indefinida"),
    tmin: float = Form(0.0), tmax: float = Form(20.0), passo: float = Form(0.5)
):
    try:
        if file:
            content = await file.read()
            df = pd.read_csv(BytesIO(content), sep=None, engine='python') if file.filename.endswith('.csv') else pd.read_excel(BytesIO(content))
        else:
            df = pd.read_csv(StringIO(manual_data), names=['Data', 'Tmin', 'Tmax', 'NF'], header=None)

        df = rename_columns(df)
        df['Data'] = pd.to_datetime(df['Data'], errors='coerce')
        res = executar_calculo_tb(df, tmin, tmax, passo)
        
        # Metadados para o Gráfico
        mdf = pd.DataFrame(res['tabela_meteorologica'])
        best_str = str(round(res['melhor_resultado']['Temperatura (ºC)'], 2))
        idx = [i for i, v in enumerate(df['NF']) if not pd.isna(v)]

        return {
            "nome": analise,
            "best": {"temp": res['melhor_resultado']['Temperatura (ºC)'], "r2": res['melhor_resultado']['R2'], "qme": res['melhor_resultado']['QME']},
            "preview": df.head(10).astype(str).to_dict(orient="records"),
            "qme_data": {"t": [x['Temperatura (ºC)'] for x in res['tabela_erros']], "q": [x['QME'] for x in res['tabela_erros']]},
            "reg": {
                "sta": [mdf.iloc[i][best_str] for i in idx],
                "nf": df['NF'].dropna().tolist(),
                "y": [mdf.iloc[i][best_str] * res['melhor_resultado']['Coef_Angular'] + res['melhor_resultado']['Intercepto'] for i in idx]
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
