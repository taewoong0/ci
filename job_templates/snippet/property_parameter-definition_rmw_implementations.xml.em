        <hudson.model.BooleanParameterDefinition>
          <name>CI_USE_GURUMDDS</name>
          <description>By setting this to True, the build will attempt to use Eclipse&apos;s Gurum DDS.</description>
          <defaultValue>@('false' if 'rmw_gurumdds_cpp' in ignore_rmw_default else 'true')</defaultValue>
        </hudson.model.BooleanParameterDefinition>
