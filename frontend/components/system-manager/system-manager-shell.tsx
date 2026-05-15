"use client";

import type { LucideIcon } from "lucide-react";
import {
  Activity,
  FileText,
  FolderKanban,
  LogIn,
  Mic2,
} from "lucide-react";
import Link from "next/link";
import { useParams, usePathname } from "next/navigation";

const NAV_ACTIVE = "bg-[#3540A8] text-white border-[#3540A8]";
const NAV_INACTIVE =
  "text-(--text) border-transparent hover:bg-black/5 dark:hover:bg-white/10";

function NavLink(props: {
  href: string;
  label: string;
  icon: LucideIcon;
  active: boolean;
}) {
  const Icon = props.icon;
  return (
    <Link
      href={props.href}
      className={`flex items-center gap-2 rounded-md border px-3 py-2 text-sm font-medium outline-none transition-colors focus-visible:ring-2 focus-visible:ring-[#3540A8] focus-visible:ring-offset-2 focus-visible:ring-offset-(--bg) ${
        props.active ? NAV_ACTIVE : NAV_INACTIVE
      }`}
      aria-current={props.active ? "page" : undefined}
    >
      <Icon className="size-4 shrink-0 opacity-95" aria-hidden />
      {props.label}
    </Link>
  );
}

export default function SystemManagerShell({
  children,
}: {
  children: React.ReactNode;
}) {
  const pathname = usePathname();
  const params = useParams();
  const rawProjectId = params?.projectId;
  const projectId =
    typeof rawProjectId === "string"
      ? rawProjectId
      : Array.isArray(rawProjectId)
        ? rawProjectId[0]
        : undefined;
  const projectIdNum = projectId != null ? Number(projectId) : NaN;
  const hasProjectContext = Number.isFinite(projectIdNum);

  return (
    <div className="flex min-h-screen w-full bg-(--bg) text-(--text)">
      <aside className="flex w-56 shrink-0 flex-col border-r border-(--border) bg-(--bg) py-6 pl-4 pr-3 md:w-60">
        <div className="mb-6 px-2">
          <div className="text-xs font-semibold uppercase tracking-wide text-(--text) opacity-60">
            System manager
          </div>
        </div>
        <nav className="flex flex-1 flex-col gap-1" aria-label="System manager">
          <NavLink
            href="/system-manager/projects"
            label="Projects"
            icon={FolderKanban}
            active={pathname === "/system-manager/projects"}
          />
          <NavLink
            href="/system-manager/discovery-state"
            label="Discovery state"
            icon={Activity}
            active={pathname === "/system-manager/discovery-state"}
          />
          {hasProjectContext ? (
            <div className="mt-4 border-t border-(--border) pt-4">
              <div className="mb-2 px-2 text-xs font-medium text-(--text) opacity-70">
                Project #{projectIdNum}
              </div>
              <NavLink
                href={`/system-manager/projects/${projectIdNum}/interviews`}
                label="Interviews"
                icon={Mic2}
                active={pathname.includes(`/projects/${projectIdNum}/interviews`)}
              />
              <NavLink
                href={`/system-manager/projects/${projectIdNum}/documents`}
                label="Documents"
                icon={FileText}
                active={pathname.includes(`/projects/${projectIdNum}/documents`)}
              />
            </div>
          ) : null}
        </nav>
        <div className="mt-auto border-t border-(--border) pt-4">
          <Link
            href="/"
            className={`flex items-center gap-2 rounded-md border px-3 py-2 text-sm outline-none transition-colors focus-visible:ring-2 focus-visible:ring-[#3540A8] focus-visible:ring-offset-2 focus-visible:ring-offset-(--bg) ${NAV_INACTIVE}`}
          >
            <LogIn className="size-4 shrink-0 opacity-95" aria-hidden />
            Hub sign-in
          </Link>
        </div>
      </aside>
      <main className="min-h-screen min-w-0 flex-1 overflow-auto">{children}</main>
    </div>
  );
}
