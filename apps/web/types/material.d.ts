import type * as React from "react";

type MaterialElementProps = React.DetailedHTMLProps<
  React.HTMLAttributes<HTMLElement>,
  HTMLElement
> & {
  [key: string]: unknown;
};

declare global {
  namespace React.JSX {
    interface IntrinsicElements {
      "md-filled-button": MaterialElementProps;
      "md-filled-tonal-button": MaterialElementProps;
      "md-filled-tonal-icon-button": MaterialElementProps;
      "md-outlined-button": MaterialElementProps;
      "md-elevated-button": MaterialElementProps;
      "md-icon-button": MaterialElementProps;
      "md-circular-progress": MaterialElementProps;
      "md-standard-top-app-bar": MaterialElementProps;
      "md-linear-progress": MaterialElementProps;
      "md-list-item": MaterialElementProps;
      "md-list": MaterialElementProps;
    }
  }
}

export {};
