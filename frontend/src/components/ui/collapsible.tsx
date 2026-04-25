import * as React from "react";

interface CollapsibleProps {
  open?: boolean;
  onOpenChange?: (open: boolean) => void;
  children: React.ReactNode;
  className?: string;
}

function Collapsible({ open = false, onOpenChange, children, className }: CollapsibleProps) {
  return (
    <div className={className} data-state={open ? "open" : "closed"}>
      {React.Children.map(children, (child) => {
        if (React.isValidElement(child)) {
          if (child.type === CollapsibleTrigger) return child;
          if (child.type === CollapsibleContent) {
            return React.cloneElement(child as React.ReactElement<CollapsibleContentProps>, { open });
          }
        }
        return child;
      })}
    </div>
  );
}

interface CollapsibleTriggerProps {
  asChild?: boolean;
  children: React.ReactNode;
  className?: string;
}

function CollapsibleTrigger({ asChild, children, className }: CollapsibleTriggerProps) {
  if (asChild && React.isValidElement(children)) {
    return children;
  }
  return <div className={className}>{children}</div>;
}

interface CollapsibleContentProps {
  open?: boolean;
  children: React.ReactNode;
  className?: string;
}

function CollapsibleContent({ open, children, className }: CollapsibleContentProps) {
  if (!open) return null;
  return <div className={className}>{children}</div>;
}

export { Collapsible, CollapsibleTrigger, CollapsibleContent };
