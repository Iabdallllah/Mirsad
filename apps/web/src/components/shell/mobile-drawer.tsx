"use client";

import * as Dialog from "@radix-ui/react-dialog";
import { Menu, X } from "lucide-react";

/**
 * Focus-trapped drawer for < 1024px (design.md §7.1, §9.1).
 * Radix handles focus trap, Esc, and focus restoration.
 */
export function MobileDrawer({ children }: { children: React.ReactNode }) {
  return (
    <Dialog.Root>
      <Dialog.Trigger asChild>
        <button
          type="button"
          className="inline-flex size-11 items-center justify-center rounded-md border border-border text-text-muted hover:bg-surface-2"
          aria-label="Open navigation menu"
        >
          <Menu aria-hidden="true" className="size-5" />
        </button>
      </Dialog.Trigger>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-40 bg-bg/80" />
        <Dialog.Content className="fixed inset-y-0 left-0 z-50 flex w-80 max-w-[85vw] flex-col overflow-y-auto border-r border-border bg-bg p-6">
          <div className="flex items-center justify-between">
            <Dialog.Title className="font-display text-xl font-bold text-text">Mirsad</Dialog.Title>
            <Dialog.Close asChild>
              <button
                type="button"
                className="inline-flex size-11 items-center justify-center rounded-md text-text-muted hover:bg-surface-2"
                aria-label="Close navigation menu"
              >
                <X aria-hidden="true" className="size-5" />
              </button>
            </Dialog.Close>
          </div>
          <div className="mt-6">{children}</div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
