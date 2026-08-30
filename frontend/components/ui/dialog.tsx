"use client"

import * as React from "react"
import { XIcon } from "lucide-react"
import { Dialog as DialogPrimitive } from "radix-ui"

import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"

/**
 * [ROOT-001 방어 패치]
 * 현상: Dialog 종료 후 overlay/content가 data-state="closed" 채 DOM에 잔존하고
 *      body의 pointer-events:none(모달 열림 시 Radix가 설정)이 해제되지 않아
 *      페이지 전체 스크롤·클릭이 먹통이 되는 이슈 (2026-08-30 QA).
 * 원인: animate-out 종료 애니메이션의 animationend가 Radix에 전달되지 않아
 *      언마운트/포인터 복구가 트리거되지 않음 (radix-ui@1.4.3 + react@19.2.8).
 * 방어: closed 상태에서 강제 hidden — 시각적 잔존·클릭 가로챔을 차단.
 *      추가로 body의 잔존 pointer-events를 감시해 원복하는 전역 가드를 띄운다.
 */

// Dialog 생명주기 동안만 활성화되는 body pointer-events 복구 가드.
// Radix가 열림 때 body에 심은 pointer-events:none이 닫힌 뒤에도 남아 있는 경우를 원복한다.
function useBodyPointerEventsGuard(open: boolean) {
  React.useEffect(() => {
    if (open) return // 열려 있는 동안은 Radix 동작 방해 금지
    const body = document.body
    const cleared = () => {
      if (body.getAttribute('style')?.includes('pointer-events: none')) {
        body.style.removeProperty('pointer-events')
      }
    }
    // 닫힘 직후 + 애니메이션 여유시간(600ms) + 최후 2.5s 타이밍에 정리
    const timers = [0, 600, 2500].map((ms) => window.setTimeout(cleared, ms))
    // 잔존 overlay/content가 DOM에 남아 있으면 숨김 (hidden 방어선 보완)
    const sweep = () => {
      document
        .querySelectorAll('[data-state="closed"][data-slot="dialog-overlay"], [data-state="closed"][data-slot="dialog-content"]')
        .forEach((el) => {
          (el as HTMLElement).style.display = 'none'
        })
    }
    const sweepTimers = [50, 700, 2600].map((ms) => window.setTimeout(sweep, ms))
    return () => {
      timers.forEach(clearTimeout)
      sweepTimers.forEach(clearTimeout)
    }
  }, [open])
}

function Dialog({
  open,
  ...props
}: React.ComponentProps<typeof DialogPrimitive.Root>) {
  useBodyPointerEventsGuard(Boolean(open))
  return <DialogPrimitive.Root data-slot="dialog" open={open} {...props} />
}

function DialogTrigger({
  ...props
}: React.ComponentProps<typeof DialogPrimitive.Trigger>) {
  return <DialogPrimitive.Trigger data-slot="dialog-trigger" {...props} />
}

function DialogPortal({
  ...props
}: React.ComponentProps<typeof DialogPrimitive.Portal>) {
  return <DialogPrimitive.Portal data-slot="dialog-portal" {...props} />
}

function DialogClose({
  ...props
}: React.ComponentProps<typeof DialogPrimitive.Close>) {
  return <DialogPrimitive.Close data-slot="dialog-close" {...props} />
}

function DialogOverlay({
  className,
  ...props
}: React.ComponentProps<typeof DialogPrimitive.Overlay>) {
  return (
    <DialogPrimitive.Overlay
      data-slot="dialog-overlay"
      className={cn(
        "data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0 data-[state=closed]:hidden fixed inset-0 z-50 bg-black/50",
        className
      )}
      {...props}
    />
  )
}

function DialogContent({
  className,
  children,
  showCloseButton = true,
  ...props
}: React.ComponentProps<typeof DialogPrimitive.Content> & {
  showCloseButton?: boolean
}) {
  return (
    <DialogPortal data-slot="dialog-portal">
      <DialogOverlay />
      <DialogPrimitive.Content
        data-slot="dialog-content"
        className={cn(
          "bg-background data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0 data-[state=closed]:zoom-out-95 data-[state=open]:zoom-in-95 data-[state=closed]:hidden fixed top-[50%] left-[50%] z-50 grid w-full max-w-[calc(100%-2rem)] translate-x-[-50%] translate-y-[-50%] gap-4 rounded-lg border p-6 shadow-lg duration-200 outline-none sm:max-w-lg",
          className
        )}
        {...props}
      >
        {children}
        {showCloseButton && (
          <DialogPrimitive.Close
            data-slot="dialog-close"
            className="ring-offset-background focus:ring-ring data-[state=open]:bg-accent data-[state=open]:text-muted-foreground absolute top-4 right-4 rounded-xs opacity-70 transition-opacity hover:opacity-100 focus:ring-2 focus:ring-offset-2 focus:outline-hidden disabled:pointer-events-none [&_svg]:pointer-events-none [&_svg]:shrink-0 [&_svg:not([class*='size-'])]:size-4"
          >
            <XIcon />
            <span className="sr-only">Close</span>
          </DialogPrimitive.Close>
        )}
      </DialogPrimitive.Content>
    </DialogPortal>
  )
}

function DialogHeader({ className, ...props }: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="dialog-header"
      className={cn("flex flex-col gap-2 text-center sm:text-left", className)}
      {...props}
    />
  )
}

function DialogFooter({
  className,
  showCloseButton = false,
  children,
  ...props
}: React.ComponentProps<"div"> & {
  showCloseButton?: boolean
}) {
  return (
    <div
      data-slot="dialog-footer"
      className={cn(
        "flex flex-col-reverse gap-2 sm:flex-row sm:justify-end",
        className
      )}
      {...props}
    >
      {children}
      {showCloseButton && (
        <DialogPrimitive.Close asChild>
          <Button variant="outline">Close</Button>
        </DialogPrimitive.Close>
      )}
    </div>
  )
}

function DialogTitle({
  className,
  ...props
}: React.ComponentProps<typeof DialogPrimitive.Title>) {
  return (
    <DialogPrimitive.Title
      data-slot="dialog-title"
      className={cn("text-lg leading-none font-semibold", className)}
      {...props}
    />
  )
}

function DialogDescription({
  className,
  ...props
}: React.ComponentProps<typeof DialogPrimitive.Description>) {
  return (
    <DialogPrimitive.Description
      data-slot="dialog-description"
      className={cn("text-muted-foreground text-sm", className)}
      {...props}
    />
  )
}

export {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogOverlay,
  DialogPortal,
  DialogTitle,
  DialogTrigger,
}
