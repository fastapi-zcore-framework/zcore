<p align="center">
  <img src="https://raw.githubusercontent.com/fastapi-zcore-framework/zcore/master/docs/assets/banner.png" alt="ZCore Logo" width="600">
  <br>
  <strong>A modest and practical architectural layer built on top of FastAPI.</strong>
</p>

<p align="center">
  <a href="https://github.com/fastapi-zcore-framework/zcore/blob/master/LICENSE">
  <img src="https://img.shields.io/github/license/fastapi-zcore-framework/zcore" alt="License"></a>
  <a href="https://pypi.org/project/fastapi-zcore-framework/"><img src="https://img.shields.io/pypi/v/fastapi-zcore-framework" alt="PyPI"></a>
  <a href="https://github.com/fastapi-zcore-framework/zcore/actions"><img src="https://img.shields.io/github/actions/workflow/status/fastapi-zcore-framework/zcore/publish.yml" alt="Build Status"></a>
</p>

---

## What is ZCore?

ZCore is not a replacement for FastAPI; it is a modest and practical architectural layer built on top of it. While FastAPI provides the high-performance engine for handling HTTP requests, ZCore provides the "chassis"—a structured environment that solves common challenges in medium-to-large scale applications such as dependency management, transaction integrity, and data leakage prevention.

The framework focuses on **Engineered Simplicity**. It abstracts complex patterns like the *Unit of Work* and *Scoped Inversion of Control* into intuitive interfaces, allowing you to focus on your domain logic while the framework ensures that your database transactions are atomic and your sensitive data remains restricted based on the execution context.

---

## Why Choose ZCore?

ZCore was designed to bridge the gap between "writing an endpoint" and "building a maintainable system."

| Feature | Standard FastAPI Challenge | The ZCore Approach |
| :--- | :--- | :--- |
| **Dependency Injection** | Manual wiring and complex `Depends` chains. | Automated **Scoped IoC** with constructor injection. |
| **Data Security** | Manual filtering of Pydantic models for different users. | Context-aware **Response Pruning** via `ResponseProjector`. |
| **Transactions** | Scatterred `.commit()` calls leading to partial failures. | Centralized **Unit of Work** (UOW) for atomic operations. |
| **Project Structure** | Inconsistent layouts across different teams. | Modular **Plugin System** and standardized CLI scaffolding. |
| **Search & Filter** | Writing repetitive boilerplate for every query. | A secure, dynamic **Search Engine** with depth-limit protection. |

---

## The Request Lifecycle

Understanding how a request travels through ZCore is key to mastering its architecture. The following diagram illustrates the automated orchestration from the moment a request hits the server to the final pruned response.

<p align="center">
  <img src="https://raw.githubusercontent.com/fastapi-zcore-framework/zcore/master/docs/assets/request-lifecycle.png" alt="ZCore Request Lifecycle" width="700">
</p>

---

## ⚡ Quick Start

### 1. Installation
Set up a clean virtual environment and install ZCore with all optional dependencies:

```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install fastapi-zcore-framework[all]
```

### 2. Scaffold a Project
Initialize your project and generate a structured domain module using our command-line utility:

```bash
# Initialize project workspace
zc init product_api
cd product_api

# Scaffold a domain app with boilerplate templates
zc startapp products -t
```

### 3. Run the Development Server
Launch the local Uvicorn development server:

```bash
zc run
```

---

## 📚 Core Pillars at a Glance

*   **⚡ Scoped IoC Container:** Manage object lifecycles (Singleton, Transient, or Scoped) with ease. Scoped dependencies are automatically cleared at the end of every HTTP request to prevent memory pollution.
*   **🛡️ Secure Search Engine:** A dynamic query builder that supports nested filters and eager-loading, while automatically blocking access to restricted database columns based on security policies.
*   **🔗 Unit of Work (UOW):** Ensures that business operations succeed or fail as a single unit. It coordinates database flushes and delays event dispatching until the transaction is successfully committed.
*   **🏗️ Modular Plugin System:** Organize your application into decoupled domains. Each plugin manages its own lifecycle hooks (`on_startup`, `on_shutdown`) and can declare dependencies on other plugins.

---

## 📖 Documentation & Learning

To explore the full capabilities of ZCore, please refer to our online documentation:

> ℹ️ **NOTE:** **[Getting Started Guide]** - Step-by-step tutorial to build your first service.

> 💡 **TIP:** **[Architectural Concepts]** - Understand the inner mechanics of our Scoped DI, UOW, and the Core Kernel.

> ⚠️ **IMPORTANT:** For production environments, remember to generate a secure secret key using the `zc gensecret` CLI command and update your `.env` configuration file.

---

<p align="center">
    <small>ZCore is licensed under the Apache License 2.0. Built with ☕ and architectural rigor.</small>
</p>
