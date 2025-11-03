# TrainPPTAgent Ollama 模型设置脚本
# 用于 Docker 环境下拉取必要的 LLM 和嵌入模型

Write-Host "=== TrainPPTAgent Ollama 模型设置 ===" -ForegroundColor Green

# 检查 Docker 是否运行
Write-Host "检查 Docker 服务状态..." -ForegroundColor Yellow
try {
    docker version | Out-Null
    Write-Host "✓ Docker 服务正常运行" -ForegroundColor Green
} catch {
    Write-Host "✗ Docker 服务未运行，请先启动 Docker" -ForegroundColor Red
    exit 1
}

# 启动服务
Write-Host "启动 TrainPPTAgent 服务..." -ForegroundColor Yellow
docker compose up -d

# 等待 Ollama 服务启动
Write-Host "等待 Ollama 服务启动..." -ForegroundColor Yellow
Start-Sleep -Seconds 10

# 检查 Ollama 服务状态（使用 ollama CLI）
Write-Host "检查 Ollama 服务状态..." -ForegroundColor Yellow
docker exec ollama ollama list | Out-Null
if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ Ollama 服务启动成功" -ForegroundColor Green
} else {
    Write-Host "✗ Ollama 服务启动失败" -ForegroundColor Red
    exit 1
}

# 拉取 LLM 模型 (qwen2.5:14b)
# Write-Host "拉取 LLM 模型 qwen2.5:14b..." -ForegroundColor Yellow
# Write-Host "注意：此模型约 8.7GB，首次下载需要较长时间" -ForegroundColor Cyan
# docker exec -it ollama ollama pull qwen2.5:14b

# if ($LASTEXITCODE -eq 0) {
#     Write-Host "✓ LLM 模型 qwen2.5:14b 拉取成功" -ForegroundColor Green
# } else {
#     Write-Host "✗ LLM 模型拉取失败" -ForegroundColor Red
#     Write-Host "可以尝试使用更小的模型，如 qwen2.5:7b 或 qwen2.5:3b" -ForegroundColor Yellow
# }

# 拉取嵌入模型 (bge-m3)
Write-Host "拉取嵌入模型 bge-m3..." -ForegroundColor Yellow
docker exec -it ollama ollama pull bge-m3

if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ 嵌入模型 bge-m3 拉取成功" -ForegroundColor Green
} else {
    Write-Host "✗ 嵌入模型拉取失败" -ForegroundColor Red
}

# 验证模型列表
Write-Host "验证已安装的模型..." -ForegroundColor Yellow
docker exec ollama ollama list

# 测试 LLM 模型（需要模型已安装）
# Write-Host "测试 LLM 模型..." -ForegroundColor Yellow
# docker exec ollama ollama run qwen2.5:14b "你好" | Out-Null
# if ($LASTEXITCODE -eq 0) {
#     Write-Host "✓ LLM 模型测试成功" -ForegroundColor Green
# } else {
#     Write-Host "✗ LLM 模型测试失败（请确认模型已下载）" -ForegroundColor Red
# }

# 测试嵌入模型（需要模型已安装）
Write-Host "测试嵌入模型..." -ForegroundColor Yellow
docker exec ollama ollama embed -m mxbai-embed-large -p "测试文本" | Out-Null
if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ 嵌入模型测试成功" -ForegroundColor Green
} else {
    Write-Host "✗ 嵌入模型测试失败（请确认模型已下载）" -ForegroundColor Red
}

Write-Host "=== 设置完成 ===" -ForegroundColor Green
Write-Host "现在可以访问以下服务：" -ForegroundColor Cyan
Write-Host "- 前端界面: http://localhost:8008" -ForegroundColor White
Write-Host "- 主 API: http://localhost:6800" -ForegroundColor White
Write-Host "- 个人知识库: http://localhost:9200" -ForegroundColor White
Write-Host "- 大纲生成: http://localhost:10060" -ForegroundColor White
Write-Host "- 内容生成: http://localhost:10061" -ForegroundColor White
Write-Host "- Ollama: http://localhost:11434" -ForegroundColor White

Write-Host "`n如果模型下载失败，可以手动执行：" -ForegroundColor Yellow
Write-Host "docker exec -it ollama ollama pull qwen2.5:7b  # 使用更小的模型" -ForegroundColor White
Write-Host "docker exec -it ollama ollama pull nomic-embed-text  # 使用更小的嵌入模型" -ForegroundColor White