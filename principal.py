import os
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse
import pandas as pd
from io import BytesIO
import stripe
from motor import executar_calculo_tb, rename_columns

app = FastAPI()

# Configuração do Stripe
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

# --- O QUE O USUÁRIO VÊ (INTERFACE) ---
@app.get("/", response_class=HTMLResponse)
async def interface():
    return """
    <!DOCTYPE html>
    <html lang="pt-br">
    <head>
        <meta charset="UTF-8"><title>EstimaTB Pro</title>
        <script src="https://cdn.tailwindcss.com"></script>
    </head>
    <body class="bg-gray-100 p-8">
        <div class="max-w-2xl mx-auto bg-white p-6 rounded-xl shadow">
            <h1 class="text-3xl font-bold text-green-700 text-center mb-6">EstimaTB 🌿</h1>
            <p class="mb-4 text-gray-600 text-center">Estimativa de Temperatura Basal de Plantas</p>
            
            <input type="file" id="arquivo" class="mb-4 block w-full text-sm text-gray-500">
            <button onclick="calcular()" id="btn" class="w-full bg-green-600 text-white py-3 rounded hover:bg-green-700">Analisar Dados</button>
            
            <div id="resultado" class="hidden mt-6 border-t pt-4">
                <div class="grid grid-cols-2 gap-4">
                    <div class="p-3 bg-gray-50 rounded">Tb Estimada: <strong id="res_tb" class="text-green-600">--</strong></div>
                    <div class="p-3 bg-gray-50 rounded">Precisão (R²): <strong id="res_r2" class="text-blue-600">--</strong></div>
                </div>
                <div class="mt-4 p-4 bg-yellow-50 text-center rounded border border-yellow-200">
                    <p class="text-sm mb-2">Deseja o relatório Excel detalhado?</p>
                    <button onclick="pagar()" class="bg-yellow-600 text-white px-4 py-1 rounded">💳 Pagar para Baixar Relatório</button>
                </div>
            </div>
        </div>
        <script>
            async function calcular() {
                const btn = document.getElementById('btn');
                const fileInput = document.getElementById('arquivo');
                if(!fileInput.files[0]) return alert("Selecione um arquivo!");
                
                btn.innerText = "Calculando...";
                const formData = new FormData();
                formData.append('file', fileInput.files[0]);

                const response = await fetch('/analisar', { method: 'POST', body: formData });
                const data = await response.json();
                
                document.getElementById('resultado').classList.remove('hidden');
                document.getElementById('res_tb').innerText = data.tb_estimada + " ºC";
                document.getElementById('res_r2').innerText = data.r2.toFixed(3);
                btn.innerText = "Analisar Dados";
            }
            async function pagar() {
                const res = await fetch('/checkout-stripe');
                const data = await res.json();
                window.location.href = data.url;
            }
        </script>
    </body>
    </html>
    """

# --- O QUE O SERVIDOR FAZ (CÁLCULOS) ---
@app.post("/analisar")
async def analisar_dados(file: UploadFile = File(...)):
    content = await file.read()
    try:
        if file.filename.endswith('.csv'):
            df = pd.read_csv(BytesIO(content), sep=None, engine='python')
        else:
            df = pd.read_excel(BytesIO(content))

        df = rename_columns(df)
        df['Data'] = pd.to_datetime(df['Data'], errors='coerce')
        resultado = executar_calculo_tb(df, 0, 20, 0.5)

        return {
            "tb_estimada": resultado['melhor_resultado']['Temperatura (ºC)'],
            "r2": resultado['melhor_resultado']['R2']
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/checkout-stripe")
def criar_checkout():
    session = stripe.checkout.Session.create(
        payment_method_types=['card', 'pix'],
        line_items=[{'price_data': {'currency': 'brl', 'product_data': {'name': 'Relatório EstimaTB Pro'}, 'unit_amount': 2500}, 'quantity': 1}],
        mode='payment',
        success_url='https://seu-link-final.com', # Pode ser seu link do Render
        cancel_url='https://seu-link-final.com',
    )
    return {"url": session.url}
