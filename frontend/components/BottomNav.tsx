"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import AppIcon from "@/components/AppIcon";

export default function BottomNav() {
  const pathname = usePathname();
  const items = [
    { href: "/today", label: "每日资讯", icon: "daily" as const },
    { href: "/programs", label: "个人节目", icon: "programs" as const },
    { href: "/account", label: "我的", icon: "account" as const },
  ];

  return (
    <nav className="bottom-nav" aria-label="主导航">
      <div className="bottom-nav__inner">
        {items.map((item) => {
          const active = pathname.startsWith(item.href);
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`bottom-nav__item ${active ? "is-active" : ""}`}
              aria-current={active ? "page" : undefined}
            >
              <span className="bottom-nav__icon">
                <AppIcon
                  name={item.icon}
                  size={21}
                  strokeWidth={1.75}
                  filled={active}
                />
              </span>
              <span>{item.label}</span>
            </Link>
          );
        })}
      </div>
    </nav>
  );
}
