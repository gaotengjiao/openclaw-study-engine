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

    // 显示用户消息
    appendMessage('user', content);
    input.value = '';

    try {
        // 修正路径：必须与 ingest.py 路由和 main.py 的 prefix 严格对应
        const response = await fetch('/api/v1/ingest/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                user_id: "adam_37",
                subject: "AI算法",
                concept: "Transformer",
                content: content
            })
        });

        if (!response.ok) {
            const errorText = await response.text();
            throw new Error(`请求失败: ${response.status} - ${errorText}`);
        }

        const data = await response.json();

        // 渲染评估结果
        let aiText = "";
        if (data.evaluation) {
            aiText = `【得分：${data.evaluation.score || 0}】\n${data.evaluation.feedback || "录入成功"}`;
        } else {
            aiText = "已同步学习进度到知识库。";
        }

        appendMessage('ai', aiText);

    } catch (error) {
        console.error('Fetch Error:', error);
        appendMessage('ai', `系统提示: ${error.message}`);
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