import * as React from "react";
import { cn } from "@/lib/utils";

// Pure CSS tooltip — no Radix dependency. Uses Tailwind group-hover.

function TooltipProvider({ children }: { children: React.ReactNode }) {
  return <>{children}</>;
}

// Tooltip wraps trigger + content in a relative group container
function Tooltip({ children }: { children: React.ReactNode }) {
  return <span className="relative group inline-block">{children}</span>;
}

interface TooltipTriggerProps extends React.HTMLAttributes<HTMLSpanElement> {
  asChild?: boolean;
  children: React.ReactNode;
}

const TooltipTrigger = React.forwardRef<HTMLSpanElement, TooltipTriggerProps>(
  ({ asChild, children, className, ...props }, ref) => {
    if (asChild && React.isValidElement(children)) {
      return React.cloneElement(children as React.ReactElement<React.HTMLAttributes<HTMLElement>>, {
        ...props,
      });
    }
    return (
      <span ref={ref} className={cn("cursor-default", className)} {...props}>
        {children}
      </span>
    );
  }
);
TooltipTrigger.displayName = "TooltipTrigger";

const TooltipContent = React.forwardRef<HTMLSpanElement, React.HTMLAttributes<HTMLSpanElement>>(
  ({ className, children, ...props }, ref) => (
    <span
      ref={ref}
      role="tooltip"
      className={cn(
        "absolute z-50 bottom-full left-1/2 -translate-x-1/2 mb-1.5",
        "bg-gray-900 text-white text-xs rounded px-2 py-1 whitespace-nowrap",
        "opacity-0 group-hover:opacity-100 pointer-events-none transition-opacity duration-150",
        className
      )}
      {...props}
    >
      {children}
    </span>
  )
);
TooltipContent.displayName = "TooltipContent";

export { TooltipProvider, Tooltip, TooltipTrigger, TooltipContent };
