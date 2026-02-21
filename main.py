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
# 🔒 BLOCO 1: LOGIN (BLINDADO)
# =========================================================================
SURL = "https://iuhtopexunirguxmjiey.supabase.co"
SKEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Iml1aHRvcGV4dW5pcmd1eG1qaWV5Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzE1MjIzNTcsImV4cCI6MjA4NzA5ODM1N30.EjDui9gQ5AlRaNpoVQisGUoXmK3j74gwzq9QSguxq78"
stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "")
ADM_MAIL = "abielgm@icloud.com"

# =========================================================================
# 🧬 BLOCO 2: EXPORTAÇÃO EXCEL
# =========================================================================
def gerar_relatorio_excel(clima, erros, reg, tb):
    out = BytesIO()
    with pd.ExcelWriter(out, engine='xlsxwriter') as wr:
        clima.to_excel(wr, sheet_name='Base_Meteorologica', index=False)
        reg.to_excel(wr, sheet_name='Resultados_STa_Ajustada', index=False)
        erros.to_excel(wr, sheet_name='Analise_QME', index=False)
        wb = wr.book
        dt_f = wb.add_format({'num_format': 'dd/mm/yyyy'})
        if 'Resultados_STa_Ajustada' in wr.sheets:
            wr.sheets['Resultados_STa_Ajustada'].set_column('A:A', 12, dt_f)
        c = wb.add_chart({'type': 'scatter', 'subtype': 'smooth'})
        c.add_series({'name': 'Erro', 'categories':['Analise_QME', 1, 0, len(erros), 0], 'values':['Analise_QME', 1, 2, len(erros), 2]})
        wr.sheets['Analise_QME'].insert_chart('E2', c)
    return base64.b64encode(out.getvalue()).decode()

def limpar_texto(t):
    if not isinstance(t, str): return t
    return "".join(c for c in unicodedata.normalize('NFKD', t) if not unicodedata.combining(c)).lower().strip()

# =========================================================================
# 🎨 BLOCO 3: INTERFACE DO SITE (CORRIGIDA)
# =========================================================================
@app.get("/", response_class=HTMLResponse)
async def carregar_site():
    html_code = """
    <!DOCTYPE html>
    <html lang="pt-br">
    <head>
        <meta charset="UTF-8"><title>EstimaTB Pro 🌿</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <script src="https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2"></script>
        <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
        <style>
            .c-input { width: 100%; border: none; padding: 6px; font-size: 11px; font-family: monospace; text-align: center; background: transparent; outline: none; }
            .c-input:focus { background-color: #f0fdf4; border-bottom: 2px solid #16a34a; }
            .t-head { background: #f8fafc; font-size: 9px; font-weight: 900; color: #64748b; padding: 12px; border: 1px solid #e2e8f0; text-transform: uppercase; }
        </style>
    </head>
    <body class="bg-slate-50 font-sans min-h-screen text-slate-800">
        
        <div id="loader" class="hidden fixed inset-0 bg-white/95 z-50 flex flex-col items-center justify-center font-black text-green-700 italic">
            <div class="animate-spin rounded-full h-16 w-16 border-t-4 border-b-4 border-green-600 mb-4"></div>
            PROCESSANDO DADOS...
        </div>

        <div class="max-w-6xl mx-auto p-4 md:p-10">
            <!-- LOGIN -->
            <div id="login-sec" class="max-w-md mx-auto bg-white p-12 rounded-[3rem] shadow-2xl mt-12 border text-center relative overflow-hidden">
                <div class="absolute top-0 left-0 w-full h-2 bg-yellow-400"></div>
                <h1 class="text-4xl font-black text-green-700 italic mb-2 uppercase underline decoration-yellow-400 decoration-4">EstimaTB🌿</h1>
                <p class="text-[9px] font-bold text-slate-300 uppercase tracking-widest mb-10 italic">Academic Hub</p>
                <div class="space-y-4">
                    <input type="email" id="email" placeholder="E-mail" class="w-full border-2 p-4 rounded-3xl mb-2 focus:border-green-600 outline-none bg-slate-50">
                    <input type="password" id="password" placeholder="Senha" class="w-full border-2 p-4 rounded-3xl mb-8 focus:border-green-600 outline-none bg-slate-50">
                    <button onclick="realizarLogin()" class="w-full bg-green-600 text-white py-5 rounded-3xl font-black shadow-xl hover:bg-green-700 transition">ENTRAR NO SISTEMA</button>
                    <button onclick="mudarModoLogin()" id="sw" class="text-green-600 font-bold text-[9px] uppercase mt-6 block mx-auto underline tracking-tighter">Criar Registro Acadêmico</button>
                </div>
            </div>

            <!-- WORKSPACE -->
            <div id="lab-sec" class="hidden animate-in fade-in duration-500">
                <div class="flex flex-col md:flex-row justify-between items-center bg-white p-6 rounded-[2.5rem] border border-slate-200 mb-8 px-10 shadow-sm">
                    <p class="font-bold text-[10px] uppercase text-slate-400 italic">Logado como: <span id="u-display" class="text-green-700 not-italic font-black text-sm ml-1 uppercase"></span></p>
                    <button onclick="fazerLogout()" class="text-red-500 font-black text-[10px] uppercase underline hover:text-red-700">Encerrar Sessão</button>
                </div>

                <div class="grid lg:grid-cols-12 gap-8">
                    <!-- Configurações -->
                    <div class="lg:col-span-5 space-y-6">
                        <div class="bg-white p-10 rounded-[3.5rem] shadow-xl border relative">
                            <h3 class="font-black text-[11px] uppercase mb-8 border-b pb-4 flex items-center italic text-slate-600"><i class="fas fa-database mr-2 text-green-600"></i>Painel de Entrada</h3>
                            
                            <label class="text-[9px] font-black text-slate-400 mb-1 ml-2 block uppercase">Nome da Análise</label>
                            <input type="text" id="a_label" class="w-full border-2 p-4 rounded-3xl mb-8 font-bold bg-slate-50 outline-none focus:border-green-500 text-sm" placeholder="Ex: Anita Época 12">

                            <div class="flex bg-slate-100 p-1.5 rounded-[2rem] mb-8 border shadow-inner">
                                <button onclick="alternarAba('f')" id="btn-f" class="flex-1 py-3 text-[10px] font-black rounded-3xl bg-white shadow-md text-green-700 uppercase transition-all">Arquivo</button>
                                <button onclick="alternarAba('m')" id="btn-m" class="flex-1 py-3 text-[10px] font-black rounded-3xl text-slate-400 uppercase transition-all">Digitação Direta</button>
                            </div>

                            <div id="box-f" class="mb-10 text-center"><input type="file" id="f_input" class="block w-full border-2 border-dashed p-10 rounded-[2.5rem] bg-slate-50 text-[10px]"></div>

                            <div id="box-m" class="hidden mb-10">
                                <div class="rounded-2xl border border-slate-200 overflow-hidden mb-2 max-h-96 overflow-y-auto bg-white shadow-inner">
                                    <table class="w-full border-collapse">
                                        <thead class="sticky top-0 z-30 shadow-sm"><tr><th class="t-head">Data</th><th class="t-head">T.Mín</th><th class="t-head">T.Máx</th><th class="t-head text-green-700">Variável (NF)</th></tr></thead>
                                        <tbody id="grid-body"></tbody>
                                    </table>
                                </div>
                                <div class="flex justify-between px-2"><button onclick="addLinha(5)" class="text-[9px] font-black text-green-600 uppercase underline">+ Linhas</button><button onclick="limparTabela()" class="text-[9px] font-bold text-red-300 uppercase italic">Limpar</button></div>
                            </div>

                            <div class="bg-slate-50 p-6 rounded-[2rem] text-center grid grid-cols-3 gap-3 mb-10 border shadow-inner">
                                <div><label class="text-[8px] font-bold uppercase text-slate-400">Tb Mín</label><input type="number" id="v_min" value="0.0" class="w-full border p-2 rounded-xl text-center font-bold"></div>
                                <div><label class="text-[8px] font-bold uppercase text-slate-400">Tb Máx</label><input type="number" id="v_max" value="20.0" class="w-full border p-2 rounded-xl text-center font-bold"></div>
                                <div><label class="text-[8px] font-black text-green-700 uppercase underline">Passo</label><input type="number" id="v_step" value="0.5" step="0.1" class="w-full border border-green-200 bg-white p-2 rounded-xl text-center font-bold text-green-700 shadow-sm"></div>
                            </div>

                            <button onclick="rodarMotor()" id="btnExe" class="w-full bg-green-600 text-white py-6 rounded-[2.5rem] font-black text-xl shadow-xl hover:scale-105 transition-all tracking-widest italic uppercase">Executar Modelagem</button>
                        </div>
                    </div>

                    <!-- Resultados -->
                    <div id="res-sec" class="lg:col-span-7 hidden animate-in slide-in-from-right duration-500">
                        <div class="bg-white p-10 rounded-[3.5rem] shadow-2xl border-t-[14px] border-slate-900 sticky top-10">
                            <h2 class="text-xl font-black italic border-b pb-6 mb-10 text-slate-800" id="res-title">Resultado da Modelagem</h2>
                             <div class="grid grid-cols-3 gap-6 mb-12 text-center">
                                <div class="bg-slate-50 p-6 rounded-[2rem] border shadow-inner"><p class="text-[9px] font-bold text-slate-400 uppercase italic mb-1">Temperatura Basal</p><p id="r-tb" class="text-4xl font-black font-mono">--</p></div>
                                <div class="bg-green-50/50 p-6 rounded-[2rem] border-2 border-green-100 shadow-inner"><p class="text-[10px] font-black text-green-700 uppercase mb-1">Ajuste (R²)</p><p id="r-r2" class="text-4xl font-black font-mono text-green-700">--</p></div>
                                <div class="bg-slate-50 p-6 rounded-[2rem] border shadow-inner"><p class="text-[9px] font-bold text-slate-400 uppercase italic mb-1">QME</p><p id="r-qme" class="text-[12px] font-black font-mono text-slate-500">--</p></div>
                             </div>
                             
                             <div class="space-y-6 mb-10">
                                <div id="gr1" class="h-64 border rounded-[2rem] p-2 bg-white"></div>
                                <div id="gr2" class="h-64 border rounded-[2rem] p-2 bg-white"></div>
                             </div>

                             <div class="border border-slate-200 rounded-[2.5rem] overflow-hidden bg-slate-50 mb-10">
                                <p class="bg-slate-100 p-4 text-[9px] font-black uppercase text-slate-500 italic ml-2">Monitor de Dados Lidos pelo Servidor</p>
                                <div id="tb-preview" class="max-h-56 overflow-auto bg-white border-t p-1"></div>
                             </div>

                             <div class="p-8 bg-amber-50 rounded-[3rem] border-2 border-amber-200 border-dotted text-center shadow-inner hover:bg-amber-100/50 transition-all">
                                <button onclick="baixarXLSX()" class="w-full bg-yellow-500 hover:bg-yellow-600 text-white font-black py-5 px-6 rounded-full text-md shadow-xl flex items-center justify-center mx-auto tracking-widest uppercase italic"><i class="fas fa-file-excel mr-3 text-2xl"></i>Baixar Relatório Completo (.XLSX)</button>
                             </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <script>
            // JS 100% Sincronizado com os IDs acima
            const U_EP = "SU_R"; const K_EP = "SK_Y"; 
            const _sb = supabase.createClient(U_EP, K_EP);
            let activeTab = 'f'; let xlsData = null; let logMode = 'login';

            function limparTabela() { document.getElementById('grid-body').innerHTML = ''; addLinha(15); }
            function addLinha(n) {
                const b = document.getElementById('grid-body');
                for(let i=0; i<n; i++){
                    const tr = document.createElement('tr'); tr.className='border-b hover:bg-slate-50 transition-colors';
                    tr.innerHTML = '<td><input type="text" class="c-input"></td><td><input type="text" class="c-input"></td><td><input type="text" class="c-input"></td><td><input type="text" class="c-input" placeholder="..."></td>';
                    b.appendChild(tr);
                }
            }
            limparTabela();

            document.addEventListener('paste', e => {
                if(e.target.classList.contains('c-input')) {
                    e.preventDefault();
                    const clip = e.clipboardData.getData('text').split(/\\r?\\n/);
                    let tr = e.target.closest('tr');
                    clip.forEach(linha => {
                        if(linha.trim() === '') return;
                        const data = linha.split('\\t'), inps = tr.querySelectorAll('input');
                        for(let i=0; i<Math.min(4, data.length, inps.length); i++){
                            inps[i].value = data[i].trim().replace(',', '.');
                        }
                        tr = tr.nextElementSibling; if(!tr){ addLinha(1); tr = document.getElementById('grid-body').lastElementChild; }
                    });
                }
            });

            async function realizarLogin() {
                const e = document.getElementById('email').value, p = document.getElementById('password').value;
                document.getElementById('loader').classList.remove('hidden');
                let {data, error} = await _sb.auth.signInWithPassword({email:e, password:p});
                if(error) { alert("Acesso Negado."); document.getElementById('loader').classList.add('hidden'); }
                else location.reload();
            }

            async function verificarSessao() {
                const {data:{user}} = await _sb.auth.getUser();
                if(user) {
                    document.getElementById('login-sec').classList.add('hidden');
                    document.getElementById('lab-sec').classList.remove('hidden');
                    document.getElementById('u-display').innerText = user.email.toLowerCase();
                }
            }
            verificarSessao();
            async function fazerLogout() { await _sb.auth.signOut(); localStorage.clear(); window.location.replace('/'); }
            
            function alternarAba(m) { 
                activeTab = m; 
                document.getElementById('btn-f').classList.toggle('bg-white', m=='f'); 
                document.getElementById('btn-m').classList.toggle('bg-white', m=='m'); 
                document.getElementById('box-f').classList.toggle('hidden', m=='m'); 
                document.getElementById('box-m').classList.toggle('hidden', m=='f'); 
            }

            try {
                    const resp = await fetch('/api/motor/run', {method:'POST', body:fd});
                    const d = await resp.json();
                    
                    // CORREÇÃO 3: Parser inteligente de erros do FastAPI
                    if(!resp.ok || d.detail) {
                        let errorMsg = d.detail;
                        if(Array.isArray(d.detail)) {
                            // Se for erro de validação do Pydantic, formata para texto legível
                            errorMsg = d.detail.map(e => `${e.loc.join('->')}: ${e.msg}`).join('\n');
                        }
                        throw new Error(errorMsg);
                    }

                    xlsData = d.xls;
                    document.getElementById('res-sec').classList.remove('hidden');

                if(activeTab === 'f') {
                    const f_obj = document.getElementById('f_input');
                    if(!f_obj.files[0]){ alert("Anexe um arquivo de dados."); document.getElementById('loader').classList.add('hidden'); return; }
                    fd.append('file', f_obj.files[0]);
                } else {
                    let linhas = [];
                    document.querySelectorAll('#grid-body tr').forEach(tr => {
                        const vals = Array.from(tr.querySelectorAll('input')).map(i => i.value.trim().replace(',', '.'));
                        if(vals[0] && vals[1] && vals[2]) {
                            if(!vals[3] || vals[3] === '') vals[3] = 'nan';
                            linhas.push(vals.join('|'));
                        }
                    });
                    if(linhas.length < 3) { alert("Faltam dados na planilha. Preencha pelo menos 3 linhas completas."); document.getElementById('loader').classList.add('hidden'); return; }
                    fd.append('manual_data', linhas.join('\\n'));
                }

                try {
                    const resp = await fetch('/api/motor/run', {method:'POST', body:fd});
                    const d = await resp.json();
                    if(d.detail) throw new Error(d.detail);

                    xlsData = d.xls;
                    document.getElementById('res-sec').classList.remove('hidden');
                    document.getElementById('r-tb').innerText = d.res.tb + "°";
                    document.getElementById('r-r2').innerText = d.res.r2.toFixed(4);
                    document.getElementById('r-qme').innerText = d.res.qme.toFixed(9);
                    document.getElementById('res-title').innerText = "🔬 Result: " + d.nome;

                    Plotly.newPlot('gr1', [{x: d.plt.qx, y: d.plt.qy, mode: 'lines+markers', line:{color:'black'}}], {title:'Estatística de Mínimo Residual QME', font:{size:10}, margin:{t:40}});
                    Plotly.newPlot('gr2', [{x: d.plt.rx, y: d.plt.ry, mode:'markers', marker:{color:'gray'}, name:'Obs.'},{x: d.plt.rx, y: d.plt.rp, mode:'lines', line:{color:'black', dash:'dot'}, name:'Modelo'}], {title:'Regressão Biológica: NF vs STa', font:{size:10}, showlegend:false, margin:{t:40}});

                    let tH = '<table class="w-full text-left font-mono text-[9px] border-collapse"><thead class="bg-slate-50 sticky top-0 border-b"><tr><th class="p-2 border-r">DATA</th><th class="p-2 border-r text-center">TMIN</th><th class="p-2 border-r text-center">TMAX</th><th class="p-2 text-center text-green-700">NF</th></tr></thead><tbody>';
                    d.preview.forEach(ri => { 
                        tH += `<tr class="border-b"><td class="p-2 border-r text-slate-500">${ri.Data}</td><td class="p-2 border-r text-center font-bold">${ri.Tmin}</td><td class="p-2 border-r text-center font-bold">${ri.Tmax}</td><td class="p-2 text-center text-green-700 font-bold">${ri.NF}</td></tr>`; 
                    });
                    document.getElementById('tb-preview').innerHTML = tH + '</tbody></table>';

                    window.scrollTo({top: document.body.scrollHeight, behavior:'smooth'});
                } catch(e) {
                    alert("ALERTA CIENTÍFICO:\\n" + e.message);
                } finally { document.getElementById('loader').classList.add('hidden'); }
            }

            function baixarXLSX() {
                if(!xlsData) return;
                const bs = atob(xlsData), ab = new ArrayBuffer(bs.length), u8 = new Uint8Array(ab);
                for(let i=0; i<bs.length; i++) u8[i] = bs.charCodeAt(i);
                const b = new Blob([ab], {type:'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'});
                const link = document.createElement('a'); link.href = window.URL.createObjectURL(b);
                link.download = `EstimaTB_Resultado_${new Date().getTime()}.xlsx`; link.click();
            }
        </script>
    </body>
    </html>
    """.replace("SU_R", SURL).replace("SK_Y", SKEY)
    return html_code

# =========================================================================
# ⚙️ BLOCO 4: MOTOR CIENTÍFICO (ROBUSTO E OTIMIZADO)
# =========================================================================
@app.post("/api/motor/run")
async def run_engine_backend(
    # CORREÇÃO 1: Uso obrigatório do File(None) para arquivos opcionais
    file: UploadFile = File(None), 
    manual_data: str = Form(None), 
    label: str = Form(""),
    vmin: float = Form(0.0), 
    vmax: float = Form(20.0), 
    vstep: float = Form(0.5)
):
    try:
        # IMPORTAÇÃO DOS DADOS
        if file and file.filename:
            content = await file.read()
            if file.filename.endswith('.csv'):
                df = pd.read_csv(BytesIO(content), sep=None, engine='python', decimal=',')
            else:
                df = pd.read_excel(BytesIO(content))
        elif manual_data:
            # Separador PIPE (|) para blindar contra vírgulas soltas
            df = pd.read_csv(StringIO(manual_data), sep='|', names=['Data','Tmin','Tmax','NF'], header=None)
        else:
            raise ValueError("Nenhum dado fornecido. Envie um arquivo ou preencha a tabela manual.")

        # HIGIENIZAÇÃO DE COLUNAS (Evita erro de cabeçalho duplo)
        df.rename(columns=lambda x: 'Data' if limpar_texto(x) == 'data' else x, inplace=True)
        df.rename(columns=lambda x: 'Tmin' if limpar_texto(x) in ['tmin','tminima','tmín'] else x, inplace=True)
        df.rename(columns=lambda x: 'Tmax' if limpar_texto(x) in ['tmax','tmaxima','tmáx'] else x, inplace=True)
        df.rename(columns=lambda x: 'NF' if limpar_texto(x) in ['nf','variavel','variável'] else x, inplace=True)

        # TRATAMENTO NUMÉRICO AGRESSIVO
        for col in ['Tmin','Tmax','NF']:
            if col in df.columns:
                # CORREÇÃO 2: Adicionado o prefixo 'r' para Raw String no Regex
                df[col] = pd.to_numeric(
                    df[col].astype(str).str.replace(',', '.').str.replace(r'[^0-9\.\-]', '', regex=True), 
                    errors='coerce'
                )
        
        # TRATAMENTO DE DATAS
        df['Data'] = pd.to_datetime(df['Data'], dayfirst=True, errors='coerce')
        
        # Exclui linhas onde a conversão falhou
        df = df.dropna(subset=['Data','Tmin','Tmax']).sort_values('Data').reset_index(drop=True)

        # FILTRO FENOLÓGICO
        v_pheno = df.dropna(subset=['NF'])
        if len(v_pheno) < 3:
            raise ValueError(f"Foram identificados apenas {len(v_pheno)} registros de NF (Variável). O cálculo exige no mínimo 3 pontos para criar a reta de regressão.")

        # INICIO DO CÁLCULO
        df['Tmed'] = (df['Tmin'] + df['Tmax']) / 2
        p_idx = v_pheno.index
        scan_res = []
        winner = None
        min_err = float('inf')

        tb_range = np.arange(vmin, vmax + vstep, vstep)
        for t in tb_range:
            t = round(float(t), 2)
            sta_cum = (df['Tmed'] - t).clip(lower=0).cumsum()
            
            # Recorte apenas nos dias de medição
            X = sta_cum.loc[p_idx].values.reshape(-1, 1)
            y = df.loc[p_idx, 'NF'].values
            
            lr = LinearRegression().fit(X, y)
            err = mean_squared_error(y, lr.predict(X))
            r2 = lr.score(X, y)
            
            scan_res.append({'Tb': t, 'R2': r2, 'QME': err})
            
            if err < min_err:
                min_err = err
                winner = {'tb': t, 'r2': r2, 'qme': err, 'a': lr.coef_[0], 'b': lr.intercept_, 'px': sta_cum.loc[p_idx].tolist(), 'fs': sta_cum.tolist()}

        mdf = pd.DataFrame(scan_res)
        
        # EXPORTAÇÃO EXCEL
        c_exp = df[['Data','Tmin','Tmax','Tmed']].copy()
        c_exp['STa_Diaria'] = winner['fs']
        p_exp = pd.DataFrame({'Data': df.loc[p_idx, 'Data'], 'NF_Observado': df.loc[p_idx, 'NF'], 'STa_Modelo': winner['px']})

        xlsx_64 = gerar_relatorio_excel(c_exp, mdf, p_exp, winner['tb'])

        return {
            "nome": label or "Amostra Científica",
            "res": {"tb": winner['tb'], "r2": winner['r2'], "qme": winner['qme']},
            "plt": {
                "qx": mdf['Tb'].tolist(), "qy": mdf['QME'].tolist(),
                "rx": [float(x) for x in winner['px']], "ry": v_pheno['NF'].astype(float).tolist(),
                "rp": [float(x * winner['a'] + winner['b']) for x in winner['px']]
            },
            "preview": df.head(30).astype(str).to_dict(orient="records"),
            "xls": xlsx_64
        }
    except Exception as e:
        import traceback
        print(traceback.format_exc()) # Mantém o log no console do servidor para você debugar depois
        return {"detail": str(e)}
