"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import AppIcon from "@/components/AppIcon";
import { api } from "@/lib/api";
import { useMe } from "@/lib/use-me";

const CONFIRM_PHRASE = "删除全部数据";

export default function AccountSettingsPage() {
  const router = useRouter();
  const { me, loading, unauthorized } = useMe();
  const [confirmText, setConfirmText] = useState("");
  const [deleting, setDeleting] = useState(false);

  useEffect(() => {
    if (unauthorized) router.replace("/");
  }, [unauthorized, router]);

  async function logout() {
    try {
      await api("/api/v1/auth/logout", { method: "POST" });
    } finally {
      router.replace("/");
    }
  }

  async function deleteAll() {
    if (confirmText !== CONFIRM_PHRASE) return;
    setDeleting(true);
    try {
      await api("/api/v1/me/data", {
        method: "DELETE",
        body: JSON.stringify({ confirmation: confirmText }),
      });
      router.replace("/");
    } catch (error) {
      alert(error instanceof Error ? error.message : "删除失败");
      setDeleting(false);
    }
  }

  if (loading || !me) return <div className="detail-loading">正在打开设置…</div>;

  return (
    <main className="account-settings-page">
      <header className="detail-header">
        <button type="button" onClick={() => router.back()} aria-label="返回">
          <AppIcon name="chevron" size={22} />
        </button>
        <h1>设置</h1>
        <i />
      </header>

      <section className="account-settings__content">
        <div className="account-settings__profile">
          <span aria-hidden="true"><AppIcon name="account" size={34} filled /></span>
          <div><strong>亲爱的用户</strong><small>AI 学习电台听众</small></div>
        </div>

        <section className="account-settings__group">
          <h2>账号</h2>
          <button type="button" className="account-settings__logout" onClick={logout}>退出登录</button>
        </section>

        <section className="account-settings__group account-settings__danger">
          <h2>个人数据</h2>
          <p>删除后，你的节目、学习资料与音频都无法恢复。请输入“{CONFIRM_PHRASE}”确认。</p>
          <input
            value={confirmText}
            onChange={(event) => setConfirmText(event.target.value)}
            placeholder={CONFIRM_PHRASE}
            aria-label="删除确认文字"
          />
          <button
            type="button"
            onClick={deleteAll}
            disabled={confirmText !== CONFIRM_PHRASE || deleting}
          >
            {deleting ? "删除中…" : "删除全部个人数据"}
          </button>
        </section>
      </section>
    </main>
  );
}
