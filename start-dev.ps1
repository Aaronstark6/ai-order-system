cd $PSScriptRoot
conda run -n ai-order-system uvicorn app.main:app --reload
