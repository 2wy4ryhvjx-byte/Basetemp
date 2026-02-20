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
# BLOCO DE SEGURANÇA E LOGIN (BLINDADO)
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
            .spreadsheet-input { width: 100%; border: none; padding: 6px; font-size: 11px; text-align: center; }
            .spreadsheet-input:focus { background-color: #f0fdf4; outline: 2px solid #16a34a; }
            .col-header { background: #f1f5f9; font-size: 9px; font-weight: 800; color: #475569; padding: 8px; border: 1px solid #e2e8f0; text-transform: uppercase; }
        </style>
    </head>
    <body class="bg-[#F3F4F6] font-sans min-h-screen text-slate-800">
        
        <div id="loading" class="hidden fixed inset-0 bg-white/95 flex items-center justify-center z-50 flex-col">
            <div class="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-green-700 mb-4"></div>
            <p class="font-black text-green-900 animate-pulse italic">PROCESSANDO MODELO CIENTÍFICO...</p>
        </div>

        <div class="max-w-6xl mx-auto p-4 md:p-10">
            <!-- LOGIN SECTION (PROTECTED) -->
            <div id="login-section" class="max-w-md mx-auto bg-white p-10 rounded-[2.5rem] shadow-2xl mt-12 text-center border">
                <h1 class="text-4xl font-black text-green-700 italic mb-2 tracking-tighter uppercase underline decoration-yellow-400">EstimaTB🌿</h1>
                <p class="text-[9px] font-bold text-slate-300 uppercase tracking-widest mb-8 italic">System Lab Environment</p>
                <div class="space-y-4">
                    <input type="email" id="email" placeholder="E-mail" class="w-full border-2 p-4 rounded-2xl outline-none focus:border-green-600 bg-slate-50">
                    <input type="password" id="password" placeholder="Senha" class="w-full border-2 p-4 rounded-2xl outline-none focus:border-green-600 bg-slate-50">
                    <button onclick="handleAuth('login')" class="w-full bg-green-600 text-white py-4 rounded-2xl font-black shadow-lg">ENTRAR</button>
                    <button onclick="toggleMode()" id="btnSwitch" class="text-green-600 font-bold text-[10px] uppercase mt-2">Cadastro Acadêmico</button>
                </div>
            </div>

            <!-- DASHBOARD -->
            <div id="main-section" class="hidden">
                <div class="flex justify-between items-center bg-white p-6 rounded-[2rem] shadow-sm border mb-8 px-10">
                    <p class="text-slate-500 font-bold text-xs italic">Research Lab: <span id="user-display" class="text-green-700 font-black not-italic"></span></p>
                    <button onclick="logout()" class="text-red-500 font-black text-[10px] uppercase underline italic transition-all">Encerrar Lab</button>
                </div>

                <div class="grid grid-cols-1 lg:grid-cols-12 gap-8">
                    <!-- Config Side -->
                    <div class="lg:col-span-5 space-y-6">
                        <div class="bg-white p-8 rounded-[2.5rem] shadow-xl border relative">
                            <h3 class="font-black text-slate-800 text-xs uppercase mb-6 flex items-center border-b pb-4 italic underline underline-offset-8 decoration-green-300"><i class="fas fa-file-excel mr-2 text-green-600"></i>Entrada de Dados</h3>
                            
                            <input type="text" id="analise_nome" placeholder="Nome da Análise (Ex: 12 Época milho)" class="w-full border-2 p-4 rounded-2xl mb-6 bg-slate-50 text-sm focus:border-green-600 outline-none">

                            <div class="flex bg-slate-100 p-1 rounded-2xl mb-6 shadow-inner">
                                <button onclick="setMode('f')" id="btn-f" class="flex-1 py-3 text-[10px] font-black rounded-xl bg-white shadow-sm text-green-700 uppercase">Arquivo Anexo</button>
                                <button onclick="setMode('m')" id="btn-m" class="flex-1 py-3 text-[10px] font-black rounded-xl text-slate-400 uppercase tracking-tighter">Inserir Manual</button>
                            </div>

                            <!-- FILE INPUT -->
                            <div id="ui-f" class="mb-6"><input type="file" id="arquivo" class="block w-full border-2 border-dashed p-10 rounded-2xl bg-slate-50 cursor-pointer"></div>

                            <!-- MANUAL SPREADSHEET -->
                            <div id="ui-m" class="hidden">
                                <p class="text-[9px] font-black text-slate-400 uppercase mb-3 italic tracking-tight">Dica: Selecione a primeira célula e cole do Excel (Ctrl+V)</p>
                                <div class="overflow-x-auto rounded-2xl border mb-2 shadow-inner bg-gray-50 max-h-80" id="grid-parent">
                                    <table class="w-full border-collapse" id="spreadsheet">
                                        <thead>
                                            <tr>
                                                <th class="col-header">Data</th>
                                                <th class="col-header">Tmin</th>
                                                <th class="col-header">Tmax</th>
                                                <th class="col-header italic">Variável (NF)</th>
                                            </tr>
                                        </thead>
                                        <tbody id="grid-body">
                                            <!-- Linhas serão injetadas via JS -->
                                        </tbody>
                                    </table>
                                </div>
                                <div class="flex justify-between items-center mb-6">
                                    <button onclick="addGridRow(5)" class="text-[8px] font-black uppercase text-green-600">+ Inserir Linhas</button>
                                    <button onclick="resetTable()" class="text-[8px] font-black uppercase text-red-500">Limpar Planilha</button>
                                </div>
                            </div>

                            <div class="bg-slate-50 p-6 rounded-3xl mt-8 border shadow-inner">
                                <p class="text-[9px] font-black text-slate-400 uppercase italic mb-4 text-center">Configurações do Passo</p>
                                <div class="grid grid-cols-3 gap-3">
                                    <div class="flex flex-col"><label class="text-[8px] font-black text-gray-400 mb-1">Mínima</label><input type="number" id="tmin" value="0.0" class="w-full border p-2 rounded-xl text-center font-bold"></div>
                                    <div class="flex flex-col"><label class="text-[8px] font-black text-gray-400 mb-1">Máxima</label><input type="number" id="tmax" value="20.0" class="w-full border p-2 rounded-xl text-center font-bold"></div>
                                    <div class="flex flex-col"><label class="text-[8px] font-black text-gray-400 mb-1 text-green-700">Passo</label><input type="number" id="passo" value="0.5" step="0.1" class="w-full border p-2 rounded-xl text-center font-bold border-green-200"></div>
                                </div>
                            </div>

                            <button id="btnCalc" onclick="executarCalculo()" class="mt-8 w-full bg-green-600 text-white py-5 rounded-[1.5rem] font-black text-xl shadow-xl hover:bg-green-700 active:scale-95 transition-all">EXECUTAR ANÁLISE</button>
                        </div>
                    </div>

                    <!-- Gráficos Principal -->
                    <div id="results-col" class="lg:col-span-7 hidden">
                        <div class="bg-white p-8 rounded-[3rem] shadow-2xl border-t-[14px] border-slate-900 mb-8">
                            <h2 class="text-xl font-black italic border-b pb-4 mb-8" id="nome-exibicao">Relatório de Modelagem</h2>
                             <div class="grid grid-cols-3 gap-4 mb-8">
                                <div class="bg-slate-50 p-6 rounded-3xl border text-center shadow-inner"><span class="text-[9px] font-black text-slate-400 block mb-1">Tb Sugerida</span><p id="v-tb" class="text-4xl font-black font-mono tracking-tighter text-slate-800">--</p></div>
                                <div class="bg-slate-50 p-6 rounded-3xl border text-center shadow-inner border-green-100"><span class="text-[9px] font-black text-green-700 block mb-1">Coef. R²</span><p id="v-r2" class="text-4xl font-black font-mono text-green-600 tracking-tighter">--</p></div>
                                <div class="bg-slate-50 p-6 rounded-3xl border text-center shadow-inner"><span class="text-[9px] font-black text-slate-400 block mb-1 uppercase">Mín. QME</span><p id="v-qme" class="text-[14px] font-bold font-mono">--</p></div>
                             </div>
                             
                             <div class="grid grid-cols-1 md:grid-cols-2 gap-4 h-[420px]">
                                <div id="gr-qme" class="border border-gray-100 rounded-3xl bg-white h-full w-full"></div>
                                <div id="gr-reg" class="border border-gray-100 rounded-3xl bg-white h-full w-full"></div>
                             </div>

                             <div id="admin-notice" class="hidden mt-8 p-3 bg-green-50 text-green-700 text-center font-black text-[9px] uppercase italic border border-green-200 rounded-xl">✓ Master Login: Licença Vitalícia Ativa</div>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <script>
            const _supa = supabase.createClient("VARIABLE_SURL", "VARIABLE_SKEY");
            const MASTER = "abielgm@icloud.com";
            let modeInput = 'f';

            function addGridRow(count = 1) {
                const tbody = document.getElementById('grid-body');
                for(let i=0; i<count; i++) {
                    const tr = document.createElement('tr');
                    tr.classList.add('border-b');
                    tr.innerHTML = `
                        <td class="border-r"><input type="text" placeholder="YYYY-MM-DD" class="spreadsheet-input dat-c"></td>
                        <td class="border-r"><input type="text" class="spreadsheet-input tmi-c"></td>
                        <td class="border-r"><input type="text" class="spreadsheet-input tma-c"></td>
                        <td><input type="text" class="spreadsheet-input var-c" placeholder="..."></td>
                    `;
                    tbody.appendChild(tr);
                }
            }
            function resetTable() { document.getElementById('grid-body').innerHTML = ''; addGridRow(12); }
            resetTable();

            // SUPORTE AO COPIAR E COLAR DO EXCEL (ESSENCIAL)
            document.addEventListener('paste', function(e) {
                if(e.target.classList.contains('spreadsheet-input')) {
                    e.preventDefault();
                    const clipboard = e.clipboardData.getData('text');
                    const rows = clipboard.split(/\\r?\\n/);
                    let currentTr = e.target.closest('tr');
                    
                    rows.forEach(rowText => {
                        if(rowText.trim() === '') return;
                        const columns = rowText.split('\\t');
                        const inputs = currentTr.querySelectorAll('input');
                        columns.forEach((val, idx) => { if(inputs[idx]) inputs[idx].value = val.trim(); });
                        
                        currentTr = currentTr.nextElementSibling;
                        if(!currentTr) { addGridRow(1); currentTr = document.getElementById('grid-body').lastElementChild; }
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
                    if(user.email.toLowerCase() === MASTER.toLowerCase()) {
                        document.getElementById('admin-tag').classList.add('flex'); // Se usar tag específica
                        document.getElementById('admin-notice').classList.remove('hidden');
                    }
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
                    if(!f) { alert("Anexe o arquivo de entrada!"); document.getElementById('loading').classList.add('hidden'); return; }
                    fd.append('file', f);
                } else {
                    let rowsCSV = [];
                    document.querySelectorAll('#grid-body tr').forEach(tr => {
                        const dat = tr.querySelector('.dat-c').value.trim();
                        const tmi = tr.querySelec
