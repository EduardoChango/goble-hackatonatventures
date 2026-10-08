from aws_cdk import Stack
from constructs import Construct


class FrontendStack(Stack):
    """Hosting del frontend (Flask + Streamlit).

    IMPORTANTE: Amplify Hosting solo sirve sitios estáticos y SSR de Node (Next.js, Nuxt, etc.).
    No ejecuta procesos Python de larga duración como Flask o Streamlit.
    Opciones:
      - App Runner / ECS Fargate con un contenedor de apps/frontend (recomendado para Streamlit).
      - Amplify solo para una UI estática, con Flask expuesto como Lambda detrás de API Gateway.
    Decidir antes de implementar este stack.
    """

    def __init__(self, scope: Construct, construct_id: str, *, api_url: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        # TODO: definir recursos de hosting del frontend. Inyectar api_url como API_BASE_URL.
        self.api_url = api_url
