# AI 学习电台前端

这是 AI 学习电台的移动端优先 Web/PWA 前端，基于 Next.js、React、TypeScript 和 Tailwind CSS。

完整的项目介绍、后端与 Worker 启动方式及环境变量说明请阅读[根目录 README](../README.md)。

## 本地开发

需要 Node.js 24 或更新版本，以及 npm。

```bash
cp .env.example .env.local
npm ci
npm run dev
```

开发服务器默认运行在 <http://127.0.0.1:3001>。前端通过 `frontend/.env.local` 中的 `NEXT_PUBLIC_API_BASE` 连接后端；未设置时，本地开发默认使用 `http://127.0.0.1:8002`。生产环境必须把它设置为浏览器可访问的 HTTPS API 地址。

## 质量检查

```bash
npm test
npm run lint
npm run build
```
