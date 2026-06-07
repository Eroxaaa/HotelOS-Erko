const { execFileSync } = require("node:child_process");

const API = process.env.API_URL || "http://localhost:8000";
const DASHBOARD_WS = process.env.DASHBOARD_WS || "ws://localhost:3000/ws/dashboard";

const runId = `E2E_${Date.now()}`;
const seen = [];

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function request(path, options = {}) {
  const response = await fetch(`${API}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
  });
  const text = await response.text();
  const body = text ? JSON.parse(text) : null;
  if (!response.ok) {
    throw new Error(`${options.method || "GET"} ${path} failed: ${response.status} ${text}`);
  }
  return body;
}

function waitForEvent(eventName, predicate = () => true, timeoutMs = 12000) {
  const existing = seen.find((item) => item.event === eventName && predicate(item));
  if (existing) return Promise.resolve(existing);

  return new Promise((resolve, reject) => {
    const started = Date.now();
    const timer = setInterval(() => {
      const event = seen.find((item) => item.event === eventName && predicate(item));
      if (event) {
        clearInterval(timer);
        resolve(event);
      } else if (Date.now() - started > timeoutMs) {
        clearInterval(timer);
        reject(new Error(`Timed out waiting for dashboard event: ${eventName}`));
      }
    }, 100);
  });
}

function cleanupSql() {
  const commands = [
    ["reception-db", "psql", "-U", "reception_user", "-d", "reception_db", "-c", `delete from guests where guest_id like '${runId}%'; update rooms set status = 'CLEAN', guest_id = null where room_number in ('101','102','103','104');`],
    ["cleaning-db", "psql", "-U", "cleaning_user", "-d", "cleaning_db", "-c", `delete from cleaning_tasks where room_number in ('101','102','103','104') and created_at > now() - interval '10 minutes'; update cleaners set is_available = true;`],
    ["room-db", "psql", "-U", "room_user", "-d", "room_db", "-c", `delete from orders where guest_id like '${runId}%';`],
    ["maintenance-db", "psql", "-U", "maintenance_user", "-d", "maintenance_db", "-c", `delete from issues where description like '${runId}%'; update technicians set is_available = true;`],
  ];

  for (const args of commands) {
    try {
      execFileSync("docker", ["compose", "exec", "-T", ...args], { stdio: "pipe" });
    } catch (error) {
      console.error(`Cleanup warning: ${args[0]} ${error.message}`);
    }
  }
}

async function main() {
  const ws = new WebSocket(DASHBOARD_WS);
  await new Promise((resolve, reject) => {
    const timer = setTimeout(() => reject(new Error("Dashboard WebSocket did not open")), 8000);
    ws.onopen = () => {
      clearTimeout(timer);
      resolve();
    };
    ws.onerror = () => {
      clearTimeout(timer);
      reject(new Error("Dashboard WebSocket error"));
    };
  });

  ws.onmessage = (message) => {
    seen.push(JSON.parse(message.data));
  };

  await sleep(300);

  const guestId = `${runId}_GUEST`;
  const checkin = await request("/api/reception/checkin", {
    method: "POST",
    body: JSON.stringify({
      guest_id: guestId,
      full_name: `${runId} Guest`,
      room_type: "single",
      floor_preference: 1,
      proximity_preference: "none",
    }),
  });
  const roomNumber = checkin.room_number;
  await waitForEvent("checkin", (event) => event.guest_id === guestId);

  await request("/api/reception/checkout", {
    method: "POST",
    body: JSON.stringify({ guest_id: guestId, discount_percent: 0 }),
  });
  await waitForEvent("checkout", (event) => event.guest_id === guestId);
  await waitForEvent("cleaning_started", (event) => event.room_number === roomNumber);

  const cleaningTasks = await request("/api/cleaning/tasks");
  const cleaningTask = cleaningTasks.find((task) => task.room_number === roomNumber && task.status !== "completed");
  if (!cleaningTask) throw new Error("Cleaning task was not created after checkout");
  await request(`/api/cleaning/tasks/${cleaningTask.id}`, {
    method: "PATCH",
    body: JSON.stringify({ status: "completed" }),
  });
  await waitForEvent("room_cleaned", (event) => event.room_number === roomNumber);

  const issue = await request("/api/maintenance/issues", {
    method: "POST",
    body: JSON.stringify({
      room_number: roomNumber,
      description: `${runId} maintenance verification`,
      priority: "normal",
    }),
  });
  await waitForEvent("maintenance_request", (event) => event.room_number === roomNumber);
  await sleep(500);
  const roomDuringMaintenance = await request(`/api/reception/rooms/${roomNumber}`);
  if (roomDuringMaintenance.status !== "maintenance") {
    throw new Error(`Expected room ${roomNumber} to be maintenance, got ${roomDuringMaintenance.status}`);
  }
  await request(`/api/maintenance/issues/${issue.id}`, {
    method: "PATCH",
    body: JSON.stringify({ status: "completed" }),
  });
  await waitForEvent("maintenance_completed", (event) => event.room_number === roomNumber);

  const order = await request("/api/room/orders", {
    method: "POST",
    body: JSON.stringify({
      room_number: roomNumber,
      guest_id: `${runId}_ORDER`,
      category: "food",
      item_name: `${runId} Tea`,
      quantity: 1,
      unit_price: 1,
      notes: "E2E verification",
    }),
  });
  await waitForEvent("new_order", (event) => event.item_name === `${runId} Tea`);
  await request(`/api/room/orders/${order.id}`, {
    method: "PATCH",
    body: JSON.stringify({ status: "delivered" }),
  });
  await waitForEvent("order_delivered", (event) => event.order_id === order.id);

  await request("/api/chat/messages", {
    method: "POST",
    body: JSON.stringify({
      sender: "E2E",
      message: `${runId} staff note`,
      room_number: roomNumber,
    }),
  });
  await waitForEvent("chat_message", (event) => event.message === `${runId} staff note`);

  await sleep(500);
  const roomAfterEvents = await request(`/api/reception/rooms/${roomNumber}`);
  if (roomAfterEvents.status !== "clean") {
    throw new Error(`Expected room ${roomNumber} to be clean after E2E flow, got ${roomAfterEvents.status}`);
  }

  ws.close();
  cleanupSql();

  const requiredEvents = [
    "checkin",
    "checkout",
    "cleaning_started",
    "room_cleaned",
    "maintenance_request",
    "maintenance_completed",
    "new_order",
    "order_delivered",
    "chat_message",
  ];
  console.log(JSON.stringify({
    status: "ok",
    runId,
    roomNumber,
    events: requiredEvents,
  }, null, 2));
}

main().catch((error) => {
  cleanupSql();
  console.error(error.message);
  process.exit(1);
});
