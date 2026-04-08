document.addEventListener('DOMContentLoaded', () => {
    const sendBtn = document.getElementById('sendBtn');
    const userInput = document.getElementById('userInput');

    if (sendBtn) {
        sendBtn.addEventListener('click', sendMessage);
    }

    if (userInput) {
        userInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') sendMessage();
        });
    }
});

async function sendMessage() {
    const input = document.getElementById('userInput');
    const content = input.value.trim();
    if (!content) return;

    appendMessage('user', content);
    input.value = '';

    try {
        // 注意路径：如果是调用 IngestService，路径通常是 /api/v1/ingest/ingest
        const response = await fetch('/api/v1/ingest/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                user_id: "adam",
                subject: "AI算法",
                concept: "Transformer",
                content: content
            })
        });

        if (!response.ok) throw new Error(`Server error: ${response.status}`);

        const data = await response.json();

        // 解析 IngestService 返回的聚合结果
        const aiResponse = data.evaluation?.feedback || "内容已录入，AI 正在思考...";
        const score = data.evaluation?.score !== undefined ? `【得分：${data.evaluation.score}】\n` : "";

        appendMessage('ai', score + aiResponse);

    } catch (error) {
        console.error('Error:', error);
        appendMessage('ai', "抱歉，连接服务器失败。请检查后端是否正常启动。");
    }
}

function appendMessage(role, text) {
    const messagesDiv = document.getElementById('messages');
    const div = document.createElement('div');
    div.className = `msg ${role}`;
    div.innerText = text;
    messagesDiv.appendChild(div);
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
}