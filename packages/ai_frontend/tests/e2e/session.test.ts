import { expect, test } from "../fixtures";
import { generateRandomTestUser } from "../helpers";
import { AuthPage } from "../pages/auth";
import { ChatPage } from "../pages/chat";

test.describe.serial("Authentication gating", () => {
  test("redirects unauthenticated visitors to the login page", async ({ page }) => {
    const authPage = new AuthPage(page);

    await page.goto("/");
    await authPage.expectRedirectToLogin("/");
  });

  test("returns 401 for chat API calls without a session", async ({ request }) => {
    const response = await request.post("/api/chat", {
      data: {
        id: "unauthenticated-chat-test",
        message: "Hello, world!",
        selectedChatModel: "chat-model",
        selectedVisibilityType: "private",
      },
    });

    expect(response.status()).toBe(401);
    const body = await response.json();
    expect(body).toEqual({ error: "unauthorized" });
  });

  test("restores access to the home page after successful login", async ({ page }) => {
    const authPage = new AuthPage(page);
    const chatPage = new ChatPage(page);
    const user = generateRandomTestUser();

    await authPage.register(user.email, user.password);
    await authPage.expectToastToContain("Account created successfully!");

    await authPage.login(user.email, user.password);
    await chatPage.expectHomeLoaded();
  });

  test("shows an error toast and re-enables the button on invalid login", async ({ page }) => {
    const authPage = new AuthPage(page);

    await authPage.login("nobody@example.com", "wrong-password");

    await authPage.expectToastToContain("Invalid credentials!");

    const submitButton = page.getByRole("button", { name: /sign in/i });
    await expect(submitButton).toBeEnabled();
    await expect(page).toHaveURL(/\/login/);
  });
});
